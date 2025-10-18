<?php

declare(strict_types=1);


namespace Redis\Workflow;

use JsonException;
/**
 * Lightweight client for publishing workflow actions into Redis Streams.
 */
class WorkflowClient
{
    /**
     * @param object $redis Any object exposing an xAdd(string, string, array): string method (native Redis, Predis client, etc.).
     */
    public function __construct(
        private readonly object $redis,
        private readonly string $stream = 'workflow:stream'
    ) {
        if (!method_exists($this->redis, 'xAdd')) {
            throw new \InvalidArgumentException('Redis-like client must implement xAdd method.');
        }
    }

    /**
     * Publish a workflow job payload into the orchestrator stream.
     *
     * @param string $workflowId
     * @param string $action
     * @param array<string,mixed> $payload
     * @param int|null $maxAttempts Override the default retry limit (must be > 0 when provided)
     * @throws JsonException
     */
    public function dispatch(
        string $workflowId,
        string $action,
        array $payload = [],
        ?int $maxAttempts = null
    ): string
    {
        $serialized = json_encode($payload, JSON_THROW_ON_ERROR);

        $message = [
            'workflow_id' => $workflowId,
            'action' => $action,
            'payload' => $serialized,
            'attempt' => 0,
        ];

        if ($maxAttempts !== null) {
            if ($maxAttempts <= 0) {
                throw new \InvalidArgumentException('maxAttempts must be greater than zero when provided.');
            }

            $message['max_attempts'] = $maxAttempts;
        }

        return $this->redis->xAdd($this->stream, '*', $message);
    }
}
