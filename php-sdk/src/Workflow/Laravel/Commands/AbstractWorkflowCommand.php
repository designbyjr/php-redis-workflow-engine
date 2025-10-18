<?php

declare(strict_types=1);

namespace Redis\Workflow\Laravel\Commands;

use Illuminate\Console\Command;
use Redis\Workflow\Examples\ExampleWorkflow;
use Redis\Workflow\WorkflowClient;

abstract class AbstractWorkflowCommand extends Command
{
    public function __construct(private readonly WorkflowClient $client)
    {
        parent::__construct();
    }

    protected function runExampleWorkflow(string $customer): int
    {
        $workflow = new ExampleWorkflow($this->client);
        $result = $workflow->runExample(['customer_id' => $customer]);

        if (property_exists($this, 'components') && $this->components !== null) {
            $this->components->info(sprintf('Workflow finished with result: %s', $result));
        } else {
            $this->info(sprintf('Workflow finished with result: %s', $result));
        }

        return self::SUCCESS;
    }
}
