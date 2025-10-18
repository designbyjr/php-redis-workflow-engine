<?php

$redisUrl = function_exists('env') ? env('WORKFLOW_REDIS_URL', null) : getenv('WORKFLOW_REDIS_URL');
$parsedUrl = $redisUrl ? parse_url((string) $redisUrl) : [];

$host = function_exists('env') ? env('REDIS_WORKFLOW_HOST', null) : null;
$port = function_exists('env') ? env('REDIS_WORKFLOW_PORT', null) : null;
$timeout = function_exists('env') ? env('REDIS_WORKFLOW_TIMEOUT', null) : null;
$database = function_exists('env') ? env('REDIS_WORKFLOW_DATABASE', null) : null;
$password = function_exists('env') ? env('REDIS_WORKFLOW_PASSWORD', null) : null;
$stream = function_exists('env') ? env('REDIS_WORKFLOW_STREAM', null) : null;

return [
    /*
    |--------------------------------------------------------------------------
    | Redis Connection Settings
    |--------------------------------------------------------------------------
    |
    | These options control how the workflow SDK connects to Redis. Update the
    | host, port, or authentication settings to match your infrastructure.
    */

    'host' => $host
        ?? ($parsedUrl['host'] ?? null)
        ?? ($_ENV['REDIS_WORKFLOW_HOST'] ?? getenv('REDIS_WORKFLOW_HOST') ?: '127.0.0.1'),
    'port' => (int) ($port
        ?? ($parsedUrl['port'] ?? null)
        ?? ($_ENV['REDIS_WORKFLOW_PORT'] ?? getenv('REDIS_WORKFLOW_PORT') ?: 6379)),
    'timeout' => (float) ($timeout ?? ($_ENV['REDIS_WORKFLOW_TIMEOUT'] ?? getenv('REDIS_WORKFLOW_TIMEOUT') ?: 1.5)),
    'database' => (int) ($database
        ?? (isset($parsedUrl['path']) ? ltrim($parsedUrl['path'], '/') : null)
        ?? ($_ENV['REDIS_WORKFLOW_DATABASE'] ?? getenv('REDIS_WORKFLOW_DATABASE') ?: 0)),
    'password' => $password
        ?? ($parsedUrl['pass'] ?? null)
        ?? ($_ENV['REDIS_WORKFLOW_PASSWORD'] ?? getenv('REDIS_WORKFLOW_PASSWORD') ?: null),

    /*
    |--------------------------------------------------------------------------
    | Stream Name
    |--------------------------------------------------------------------------
    |
    | The Redis Stream that workflow jobs will be published to. Ensure that the
    | orchestrator is listening on this same stream name.
    */

    'stream' => $stream
        ?? ($_ENV['WORKFLOW_REDIS_STREAM'] ?? getenv('WORKFLOW_REDIS_STREAM'))
        ?? ($_ENV['REDIS_WORKFLOW_STREAM'] ?? getenv('REDIS_WORKFLOW_STREAM') ?: 'workflow:stream'),
];
