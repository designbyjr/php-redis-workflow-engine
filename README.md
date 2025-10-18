# Redis-Powered Workflow Engine (Prototype)

This repository assembles a Temporal-inspired workflow engine without gRPC or RoadRunner. Redis Streams handle orchestration, a multithreaded Python worker executes workflow steps, Postgres stores an audit trail, and the PHP SDK mirrors Temporal’s ergonomics for Laravel and Symfony teams.

```
┌───────────────┐       xAdd / Streams        ┌────────────────────┐
│ PHP Producers │ ─────────────────────────► │ Redis (Queues)      │
└──────┬────────┘                            └─────────┬──────────┘
       │                                              │ xreadgroup
       │ publish via SDK                              ▼
       │                                      ┌────────────────────┐
       └────────────────────────────────────► │ Python Worker       │
                                              │  • env validation  │
                                              │  • retries / logs  │
                                              └─────────┬──────────┘
                                                        │ inserts
                                                        ▼
                                              ┌────────────────────┐
                                              │ Postgres Action Log │
                                              └─────────┬──────────┘
                                                        │ metrics/api
                                                        ▼
                                              ┌────────────────────┐
                                              │ FastAPI Dashboard   │
                                              └────────────────────┘
```

## Components

### Python orchestration stack

* `orchestrator/env.py` – central environment manager that creates `.env.workflow`, hydrates Docker/container environments, and propagates Redis/Postgres settings into Laravel or Symfony `.env` files.
* `orchestrator/worker.py` – Redis consumer group worker that polls every 50 ms, fans jobs out to a `ThreadPoolExecutor`, and retries with `RetryPolicy` while logging every attempt to Postgres.
* `orchestrator/cli.py` – universal CLI (`python -m orchestrator.cli stack`) that validates the environment, runs the worker, and starts the dashboard. The helper script `./scripts/run_stack.py` wraps this for all environments.
* `dashboard/app.py` – FastAPI service exposing `/metrics`, `/workflows/{id}`, and `/actions/recent` using the same `MetricsCollector` instance shared with the worker.

### PHP SDK (`php-sdk/`)

* Composer package `redis/workflow-sdk` with Laravel 11/12 auto-discovery, Symfony bundle registration, and a RoadRunner-free PHP client.
* `src/Workflow/Env/EnvironmentConfigurator.php` reuses existing Redis/Postgres settings, writes workflow-specific keys into `.env`, `.env.local`, and `.env.example`, and keeps them aligned with the Python orchestrator.
* Framework commands (`workflow:run`, `workflow:env`, and `redis-workflow:*`) wrap the client for both Laravel generations and Symfony consoles.
* `src/Workflow/Examples/ExampleWorkflow.php` demonstrates Temporal-style attribute annotations for activities and workflows.

## Prerequisites

* Python 3.10–3.13 (checked by Composer’s post-install hook).
* Redis 6+
* Postgres 13+
* PHP 8.1+ with the `redis` and `ffi` extensions enabled.

## Quick start

1. **Create & verify shared environment**

   ```bash
   cp .env.workflow.example .env.workflow  # customise values if needed
   python -m orchestrator.cli env --framework-path /path/to/laravel-app --framework-path /path/to/symfony-app
   ```

   The command ensures:
   * `WORKFLOW_REDIS_URL`, `WORKFLOW_POSTGRES_DSN`, dashboard host/port, the worker poll interval, and the default retry limit are present.
   * Derived Redis keys (`REDIS_WORKFLOW_HOST`, etc.) exist so PHP can reuse them.
   * Laravel/Symfony `.env`, `.env.local`, and `.env.example` files receive the same values (without clobbering existing Redis/Postgres settings) and Docker users are prompted to persist the file.

2. **Install Python dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Launch worker + dashboard with one command**

   ```bash
   ./scripts/run_stack.py             # or: python -m orchestrator.cli stack --reload
   ```

   The CLI re-validates the environment, starts the Redis worker in a background thread, and runs the FastAPI dashboard (default `http://127.0.0.1:8000`).

4. **Install the PHP SDK**

   ```bash
   cd php-sdk
   composer install
   ```

   Composer warns if Python is outside the supported 3.10–3.13 range so the orchestration tooling remains compatible.

5. **Run the example workflow from PHP**

   ```php
   use Redis\Workflow\Examples\ExampleWorkflow;
   use Redis\Workflow\WorkflowClient;

   $redis = new Redis();
   $redis->connect(getenv('REDIS_WORKFLOW_HOST'), (int) getenv('REDIS_WORKFLOW_PORT'));

   $client = new WorkflowClient($redis, getenv('WORKFLOW_REDIS_STREAM'));
   $workflow = new ExampleWorkflow($client);

   $result = $workflow->runExample(['customer_id' => 'signup-123']);
   $resultWithOverride = $workflow->runExample([
       'customer_id' => 'signup-123',
       'max_attempts' => 8, // override WORKFLOW_MAX_RETRY_ATTEMPTS for this run
   ]);
   ```

   Or trigger the CLI binary (which automatically hydrates `.env.workflow`):

   ```bash
   php vendor/bin/workflow --customer=signup-123
   ```

## Laravel integration

1. `composer require redis/workflow-sdk`
2. Publish configuration: `php artisan vendor:publish --tag=redis-workflow-config`
3. Ensure env defaults: `php artisan workflow:env`
4. Dispatch workflows:

   ```php
   use Redis\Workflow\Laravel\Facades\WorkflowClient;

   WorkflowClient::dispatch('signup-123', 'SendWelcomeEmail', ['email' => 'user@example.com'], maxAttempts: 7);
   ```

5. Run the bundled commands:

   ```bash
   php artisan workflow:run signup-123          # Laravel 11 prompt-driven experience
   php artisan workflow:env --project=./        # Updates .env/.env.example with workflow keys
   ```

Laravel 12 apps automatically use the modern interaction style with `Laravel\Prompts`. Both versions share the same `workflow:env` signature but render feedback using their respective console UX.

## Symfony integration

1. Enable the bundle:

   ```php
   // config/bundles.php
   return [
       Redis\Workflow\Symfony\RedisWorkflowBundle::class => ['all' => true],
   ];
   ```

2. Configure Redis in `config/packages/redis_workflow.yaml` (values come from `.env.workflow`):

   ```yaml
   redis_workflow:
     host: '%env(REDIS_WORKFLOW_HOST)%'
     port: '%env(int:REDIS_WORKFLOW_PORT)%'
     stream: '%env(WORKFLOW_REDIS_STREAM)%'
   ```

3. Sync environment defaults and run workflows:

   ```bash
   php bin/console redis-workflow:env --project=./
   php bin/console redis-workflow:run signup-123
   ```

## PHP SDK API reference & examples

The SDK ships a small, focused API. The snippets below demonstrate how each
public function works in day-to-day code.

### `WorkflowClient::__construct(object $redis, string $stream = 'workflow:stream')`

Create a client by passing any Redis-like object that exposes an
`xAdd(string $key, string $id, array $values): string` method. The optional
stream argument lets you target a custom Redis Stream name.

```php
use Redis\Workflow\WorkflowClient;

$redis = new Redis();
$redis->connect('127.0.0.1', 6379);

// Target the default stream.
$client = new WorkflowClient($redis);

// Or provide a custom stream name.
$highPriority = new WorkflowClient($redis, 'workflow:stream:high-priority');
```

### `WorkflowClient::dispatch(string $workflowId, string $action, array $payload = [], ?int $maxAttempts = null): string`

Push a workflow job into Redis. The payload is JSON-encoded automatically. Pass
`$maxAttempts` to override `WORKFLOW_MAX_RETRY_ATTEMPTS` for this invocation.

```php
$messageId = $client->dispatch(
    workflowId: 'signup-123',
    action: 'stage.start',
    payload: ['email' => 'user@example.com'],
    maxAttempts: 7,
);

// The returned message ID can be stored for replay or debugging.
```

### `ExampleWorkflow::runExample(array $input): string`

Entry point for the bundled workflow example. It extracts a `customer_id`,
queues a `stage.start` action, performs a PHP-side calculation, and emits a
`stage.finish` action. The return value mirrors the activity result.

```php
use Redis\Workflow\Examples\ExampleWorkflow;

$workflow = new ExampleWorkflow($client);
$result = $workflow->runExample(['customer_id' => 'signup-123']);

// $result === 'result-for-signup-123'
```

### `ExampleWorkflow::performHeavyCalculation(string $customerId): string`

Illustrative activity-style method decorated with `#[ActivityMethod]`. Replace
its body with your long-running work; the example simply prefixes the ID.

```php
$calculated = $workflow->performHeavyCalculation('enterprise-client');

// $calculated === 'result-for-enterprise-client'
```

### `EnvironmentConfigurator::ensure(string $projectRoot): array`

Synchronise workflow environment variables into Laravel or Symfony projects. It
returns the list of `.env` files that were updated.

```php
use Redis\Workflow\Env\EnvironmentConfigurator;

$configurator = new EnvironmentConfigurator();
$updatedFiles = $configurator->ensure(base_path());

// e.g. ['/.env', '/.env.example'] when new keys were appended.
```

Laravel 11/12 and Symfony console commands call this helper internally, so
custom tooling can reuse it directly when needed.

## Observability & replay

* `WORKFLOW_POSTGRES_DSN` controls where the worker logs each attempt (`workflow_actions` table by default).
* `WORKFLOW_POLL_INTERVAL` (seconds) defines how frequently the Python worker polls Redis. The orchestrator refuses to start if this value is missing.
* `WORKFLOW_MAX_RETRY_ATTEMPTS` establishes the default retry ceiling; PHP workflows can override it per dispatch.
* The FastAPI dashboard exposes metrics and execution histories; refresh `http://127.0.0.1:8000/workflows/<workflow-id>` to replay the timeline.
* Python logging is routed through the shared `EnvironmentManager`, so Docker restarts surface helpful messages when `.env.workflow` is missing.

## Automated tests

* Python: `pytest orchestrator/tests`
* PHP / Pest: `cd php-sdk && composer test`

Composer excludes Python-oriented fixtures from archives, keeping the published package lightweight while ensuring both Pest and pytest suites run locally.
