<?php

declare(strict_types=1);

namespace Redis\Workflow\Env;

final class EnvironmentConfigurator
{
    /**
     * Default values used when the consuming application does not declare
     * workflow-specific Redis or Postgres variables.
     *
     * @var array<string, string>
     */
    private const DEFAULTS = [
        'WORKFLOW_REDIS_URL' => 'redis://127.0.0.1:6379/0',
        'WORKFLOW_REDIS_STREAM' => 'workflow:stream',
        'WORKFLOW_POSTGRES_DSN' => 'postgresql://workflow:workflow@localhost:5432/workflows',
        'WORKFLOW_DASHBOARD_HOST' => '127.0.0.1',
        'WORKFLOW_DASHBOARD_PORT' => '8000',
        'WORKFLOW_POLL_INTERVAL' => '0.05',
        'WORKFLOW_MAX_RETRY_ATTEMPTS' => '5',
    ];

    /**
     * Ensures that Laravel/Symfony `.env` files contain Redis/Postgres settings
     * compatible with the Python orchestrator. Existing Redis or Postgres
     * settings are reused to keep configuration consistent.
     *
     * @return array<int, string> List of environment files that were updated.
     */
    public function ensure(string $projectRoot): array
    {
        $paths = $this->candidatePaths($projectRoot);
        $updated = [];

        foreach ($paths as $path) {
            if (!is_file($path)) {
                continue;
            }

            $environment = $this->readEnvFile($path);
            $merged = $this->mergeValues($environment);

            if ($merged === $environment) {
                continue;
            }

            $this->writeEnvFile($path, $environment, $merged);
            $updated[] = $path;
        }

        return $updated;
    }

    /**
     * @return array<int, string>
     */
    private function candidatePaths(string $root): array
    {
        return [
            rtrim($root, '/').'/'.'.env',
            rtrim($root, '/').'/'.'.env.local',
            rtrim($root, '/').'/'.'.env.example',
        ];
    }

    /**
     * @param array<string, string> $existing
     * @return array<string, string>
     */
    private function mergeValues(array $existing): array
    {
        $redisUrl = $existing['WORKFLOW_REDIS_URL']
            ?? $existing['REDIS_URL']
            ?? $this->buildRedisUrl($existing);
        $postgresDsn = $existing['WORKFLOW_POSTGRES_DSN']
            ?? $existing['DATABASE_URL']
            ?? self::DEFAULTS['WORKFLOW_POSTGRES_DSN'];

        $values = $existing;
        $values['WORKFLOW_REDIS_URL'] = $redisUrl ?? self::DEFAULTS['WORKFLOW_REDIS_URL'];
        $values['WORKFLOW_REDIS_STREAM'] = $existing['WORKFLOW_REDIS_STREAM']
            ?? self::DEFAULTS['WORKFLOW_REDIS_STREAM'];
        $values['WORKFLOW_POSTGRES_DSN'] = $postgresDsn;
        $values['WORKFLOW_DASHBOARD_HOST'] = $existing['WORKFLOW_DASHBOARD_HOST']
            ?? self::DEFAULTS['WORKFLOW_DASHBOARD_HOST'];
        $values['WORKFLOW_DASHBOARD_PORT'] = $existing['WORKFLOW_DASHBOARD_PORT']
            ?? self::DEFAULTS['WORKFLOW_DASHBOARD_PORT'];
        $values['WORKFLOW_POLL_INTERVAL'] = $existing['WORKFLOW_POLL_INTERVAL']
            ?? self::DEFAULTS['WORKFLOW_POLL_INTERVAL'];
        $values['WORKFLOW_MAX_RETRY_ATTEMPTS'] = $existing['WORKFLOW_MAX_RETRY_ATTEMPTS']
            ?? self::DEFAULTS['WORKFLOW_MAX_RETRY_ATTEMPTS'];

        foreach ($this->phpCompatKeys($values['WORKFLOW_REDIS_URL'], $values['WORKFLOW_REDIS_STREAM']) as $key => $value) {
            if (!array_key_exists($key, $values) || $values[$key] === '') {
                $values[$key] = $value;
            }
        }

        return $values;
    }

    /**
     * @param array<string, string> $values
     */
    private function writeEnvFile(string $path, array $existing, array $values): void
    {
        $lines = file($path, FILE_IGNORE_NEW_LINES) ?: [];
        $lineIndex = [];

        foreach ($lines as $index => $line) {
            if (str_starts_with((string) $line, '#')) {
                continue;
            }

            [$key] = array_pad(explode('=', (string) $line, 2), 2, '');
            if ($key !== '') {
                $lineIndex[$key] = $index;
            }
        }

        foreach ($values as $key => $value) {
            $formatted = sprintf('%s=%s', $key, $value);
            if (isset($lineIndex[$key])) {
                $lines[$lineIndex[$key]] = $formatted;
                continue;
            }

            if (array_key_exists($key, $existing)) {
                continue;
            }

            $lines[] = $formatted;
        }

        file_put_contents($path, implode(PHP_EOL, $lines).PHP_EOL);
    }

    /**
     * @return array<string, string>
     */
    private function readEnvFile(string $path): array
    {
        $values = [];
        $contents = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) ?: [];

        foreach ($contents as $line) {
            if (str_starts_with($line, '#')) {
                continue;
            }

            $parts = explode('=', $line, 2);
            if (count($parts) !== 2) {
                continue;
            }

            [$key, $value] = $parts;
            $values[trim($key)] = trim($value, " \"'\t");
        }

        return $values;
    }

    /**
     * @param array<string, string> $existing
     */
    private function buildRedisUrl(array $existing): string
    {
        $host = $existing['REDIS_HOST'] ?? $existing['REDIS_WORKFLOW_HOST'] ?? '127.0.0.1';
        $port = $existing['REDIS_PORT'] ?? $existing['REDIS_WORKFLOW_PORT'] ?? '6379';
        $database = $existing['REDIS_DB'] ?? $existing['REDIS_WORKFLOW_DATABASE'] ?? '0';
        $password = $existing['REDIS_PASSWORD'] ?? $existing['REDIS_WORKFLOW_PASSWORD'] ?? '';

        $auth = $password !== '' ? sprintf(':%s@', $password) : '';

        return sprintf('redis://%s%s:%s/%s', $auth, $host, $port, $database);
    }

    /**
     * @return array<string, string>
     */
    private function phpCompatKeys(string $redisUrl, string $stream): array
    {
        $parts = parse_url($redisUrl) ?: [];
        $database = isset($parts['path']) ? ltrim($parts['path'], '/') : '0';

        return [
            'REDIS_WORKFLOW_HOST' => $parts['host'] ?? '127.0.0.1',
            'REDIS_WORKFLOW_PORT' => isset($parts['port']) ? (string) $parts['port'] : '6379',
            'REDIS_WORKFLOW_PASSWORD' => $parts['pass'] ?? '',
            'REDIS_WORKFLOW_DATABASE' => $database !== '' ? $database : '0',
            'REDIS_WORKFLOW_STREAM' => $stream,
        ];
    }
}
