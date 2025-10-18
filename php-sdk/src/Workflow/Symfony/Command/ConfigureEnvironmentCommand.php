<?php

declare(strict_types=1);

namespace Redis\Workflow\Symfony\Command;

use Redis\Workflow\Env\EnvironmentConfigurator;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;

#[AsCommand('redis-workflow:env', 'Ensure Redis and Postgres workflow environment variables exist.')]
final class ConfigureEnvironmentCommand extends Command
{
    protected function configure(): void
    {
        $this
            ->addOption('project', null, InputOption::VALUE_REQUIRED, 'Override the project root to scan for env files');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $project = $input->getOption('project');
        $project = is_string($project) && $project !== '' ? $project : getcwd();

        $configurator = new EnvironmentConfigurator();
        $updated = $configurator->ensure($project);

        if ($updated === []) {
            $output->writeln('<info>Workflow environment variables already configured.</info>');
            return Command::SUCCESS;
        }

        foreach ($updated as $file) {
            $output->writeln(sprintf('<info>Updated %s</info>', $file));
        }

        return Command::SUCCESS;
    }
}
