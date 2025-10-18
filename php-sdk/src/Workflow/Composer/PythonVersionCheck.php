<?php

declare(strict_types=1);

namespace Redis\Workflow\Composer;

use Composer\Script\Event;

final class PythonVersionCheck
{
    private const MIN_VERSION = '3.10.0';
    private const MAX_VERSION = '3.13.99';

    public static function handle(Event $event): void
    {
        $io = $event->getIO();
        $executable = self::discoverPythonExecutable();

        if ($executable === null) {
            $io->writeError('<warning>[redis-workflow]</warning> python3 executable was not detected. Install Python '.self::MIN_VERSION.' or newer.');
            return;
        }

        $versionOutput = @shell_exec(sprintf('%s --version 2>&1', escapeshellcmd($executable)));

        if (!is_string($versionOutput) || trim($versionOutput) === '') {
            $io->writeError(sprintf('<warning>[redis-workflow]</warning> Unable to determine %s version; ensure Python %s-%s is installed.', $executable, self::MIN_VERSION, self::MAX_VERSION));
            return;
        }

        if (!preg_match('/(\d+\.\d+\.\d+)/', $versionOutput, $matches)) {
            $io->writeError(sprintf('<warning>[redis-workflow]</warning> Unexpected version string "%s" returned by %s.', trim($versionOutput), $executable));
            return;
        }

        $version = $matches[1];

        if (version_compare($version, self::MIN_VERSION, '<')) {
            $io->writeError(sprintf('<error>[redis-workflow]</error> Python %s detected, but %s or newer is required to run the orchestration worker.', $version, self::MIN_VERSION));
            throw new \RuntimeException('Python version too old for redis-workflow.');
        }

        if (version_compare($version, self::MAX_VERSION, '>')) {
            $io->writeError(sprintf('<warning>[redis-workflow]</warning> Python %s detected. The SDK was tested up to %s; proceed with caution.', $version, self::MAX_VERSION));
        } else {
            $io->write(sprintf('<info>[redis-workflow]</info> Python %s satisfies the workflow orchestrator requirements.', $version));
        }
    }

    private static function discoverPythonExecutable(): ?string
    {
        foreach (['python3', 'python'] as $command) {
            $path = trim((string) @shell_exec(sprintf('command -v %s 2>/dev/null', escapeshellcmd($command))));
            if ($path !== '') {
                return $path;
            }
        }

        return null;
    }
}
