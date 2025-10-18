<?php

declare(strict_types=1);

namespace Redis\Workflow\Laravel\Commands;

use Illuminate\Console\Command;
use Redis\Workflow\Env\EnvironmentConfigurator;

final class Laravel12ConfigureEnvCommand extends Command
{
    protected $signature = 'workflow:env {--project= : Override the project root to scan for env files}';
    protected $description = 'Ensure Redis and Postgres workflow environment variables exist.';

    public function handle(): int
    {
        $project = (string) ($this->option('project') ?: base_path());
        $configurator = new EnvironmentConfigurator();
        $updated = $configurator->ensure($project);

        if ($updated === []) {
            $this->outputMessage('Workflow environment variables already configured.');
            return self::SUCCESS;
        }

        foreach ($updated as $file) {
            $this->outputMessage(sprintf('Updated %s', $file));
        }

        return self::SUCCESS;
    }

    private function outputMessage(string $message): void
    {
        if (property_exists($this, 'components') && $this->components !== null) {
            $this->components->info($message);
            return;
        }

        $this->info($message);
    }
}
