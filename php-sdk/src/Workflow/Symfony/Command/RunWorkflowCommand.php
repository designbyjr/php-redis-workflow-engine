<?php

declare(strict_types=1);

namespace Redis\Workflow\Symfony\Command;

use Redis\Workflow\Examples\ExampleWorkflow;
use Redis\Workflow\WorkflowClient;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputArgument;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Output\OutputInterface;

#[AsCommand(name: 'redis-workflow:run', description: 'Dispatch the example workflow through the Symfony console')]
final class RunWorkflowCommand extends Command
{
    public function __construct(private readonly WorkflowClient $client)
    {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this->addArgument('customer', InputArgument::REQUIRED, 'Customer identifier for the example workflow.');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $workflow = new ExampleWorkflow($this->client);
        $customer = (string) $input->getArgument('customer');
        $result = $workflow->runExample(['customer_id' => $customer]);

        $output->writeln(sprintf('<info>Workflow finished with result: %s</info>', $result));

        return Command::SUCCESS;
    }
}
