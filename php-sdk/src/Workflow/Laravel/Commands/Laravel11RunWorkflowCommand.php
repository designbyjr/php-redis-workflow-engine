<?php

declare(strict_types=1);

namespace Redis\Workflow\Laravel\Commands;

final class Laravel11RunWorkflowCommand extends AbstractWorkflowCommand
{
    protected $signature = 'workflow:run {customer : The customer identifier to pass to the example workflow}';
    protected $description = 'Dispatch the example workflow using Laravel 11 artisan tooling.';

    public function handle(): int
    {
        $customer = (string) $this->argument('customer');

        return $this->runExampleWorkflow($customer);
    }
}
