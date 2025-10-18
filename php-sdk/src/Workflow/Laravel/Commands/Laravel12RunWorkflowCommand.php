<?php

declare(strict_types=1);

namespace Redis\Workflow\Laravel\Commands;

final class Laravel12RunWorkflowCommand extends AbstractWorkflowCommand
{
    protected $signature = 'workflow:run {customer? : The customer identifier to pass to the example workflow} {--customer=}';
    protected $description = 'Dispatch the example workflow using the Laravel 12 interaction style.';

    public function handle(): int
    {
        $customer = $this->argument('customer') ?? $this->option('customer');
        $customer = is_string($customer) ? $customer : '';

        if ($customer === '' && function_exists('Laravel\\Prompts\\text')) {
            $customer = (string) \Laravel\Prompts\text('Customer identifier for the example workflow');
        }

        if ($customer === '') {
            $customer = (string) $this->ask('Customer identifier for the example workflow');
        }

        return $this->runExampleWorkflow($customer);
    }
}
