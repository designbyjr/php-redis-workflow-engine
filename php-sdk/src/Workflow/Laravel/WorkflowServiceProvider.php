<?php

declare(strict_types=1);

namespace Redis\Workflow\Laravel;

use Illuminate\Foundation\Application as LaravelApplication;
use Illuminate\Support\ServiceProvider;
use Redis;
use Redis\Workflow\Laravel\Commands\Laravel11ConfigureEnvCommand;
use Redis\Workflow\Laravel\Commands\Laravel11RunWorkflowCommand;
use Redis\Workflow\Laravel\Commands\Laravel12ConfigureEnvCommand;
use Redis\Workflow\Laravel\Commands\Laravel12RunWorkflowCommand;
use Redis\Workflow\WorkflowClient;

class WorkflowServiceProvider extends ServiceProvider
{
    /**
     * Register services for the Laravel container.
     */
    public function register(): void
    {
        $this->mergeConfigFrom(__DIR__ . '/../../../config/redis_workflow.php', 'redis_workflow');

        $this->app->singleton(WorkflowClient::class, function ($app) {
            $config = $app['config']->get('redis_workflow');

            $client = new Redis();
            $client->connect($config['host'], $config['port'], $config['timeout']);

            if (!empty($config['password'])) {
                $client->auth($config['password']);
            }

            if (!empty($config['database'])) {
                $client->select((int) $config['database']);
            }

            return new WorkflowClient($client, $config['stream']);
        });

        $this->app->alias(WorkflowClient::class, 'redis-workflow.client');
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        $this->publishes([
            __DIR__ . '/../../../config/redis_workflow.php' => config_path('redis_workflow.php'),
        ], 'redis-workflow-config');

        if ($this->app->runningInConsole()) {
            $this->commands($this->detectLaravelCommand());
        }
    }

    /**
     * @return array<int, class-string>
     */
    private function detectLaravelCommand(): array
    {
        $version = $this->resolveLaravelVersion();

        if ($version !== null && version_compare($version, '12.0.0', '>=')) {
            return [Laravel12RunWorkflowCommand::class, Laravel12ConfigureEnvCommand::class];
        }

        return [Laravel11RunWorkflowCommand::class, Laravel11ConfigureEnvCommand::class];
    }

    private function resolveLaravelVersion(): ?string
    {
        if (class_exists(LaravelApplication::class) && $this->app instanceof LaravelApplication) {
            return LaravelApplication::VERSION;
        }

        if (method_exists($this->app, 'version')) {
            $raw = (string) $this->app->version();
            if (preg_match('/(\d+\.\d+\.\d+)/', $raw, $matches)) {
                return $matches[1];
            }
        }

        return null;
    }
}
