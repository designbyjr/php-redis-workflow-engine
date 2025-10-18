<?php

declare(strict_types=1);

namespace Redis\Workflow\Examples;

use Redis\Workflow\Attributes\ActivityMethod;
use Redis\Workflow\Attributes\WorkflowMethod;
use Redis\Workflow\Contracts\WorkflowInterface;
use Redis\Workflow\WorkflowClient;

final class ExampleWorkflow implements WorkflowInterface
{
    public function __construct(private readonly WorkflowClient $client)
    {
    }

    public function getWorkflowId(): string
    {
        return 'example-workflow';
    }

    #[WorkflowMethod(name: 'Example.Run', timeoutSeconds: 300)]
    public function runExample(array $input): string
    {
        $customerId = $input['customer_id'] ?? 'anonymous';
        $payload = ['customer_id' => $customerId, 'stage' => 'start'];
        $maxAttempts = isset($input['max_attempts']) && (int) $input['max_attempts'] > 0
            ? (int) $input['max_attempts']
            : null;

        $this->client->dispatch($this->getWorkflowId(), 'stage.start', $payload, $maxAttempts);
        $activityResult = $this->performHeavyCalculation($customerId);
        $this->client->dispatch($this->getWorkflowId(), 'stage.finish', [
            'customer_id' => $customerId,
            'result' => $activityResult,
        ], $maxAttempts);

        return $activityResult;
    }

    #[ActivityMethod(name: 'Example.Calculate', retryLimit: 5)]
    public function performHeavyCalculation(string $customerId): string
    {
        return 'result-for-'.$customerId;
    }
}
