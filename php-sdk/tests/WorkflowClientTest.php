<?php

declare(strict_types=1);

use Redis\Workflow\Examples\ExampleWorkflow;
use Redis\Workflow\WorkflowClient;

class FakeRedis
{
    public array $lastAdd = [];

    public function xAdd(string $stream, string $id, array $payload): string
    {
        $this->lastAdd = [$stream, $id, $payload];

        return '1677721600000-0';
    }
}

test('workflow client serializes payloads and adds attempt metadata', function (): void {
    $redis = new FakeRedis();
    $client = new WorkflowClient($redis, 'workflow:stream');

    $id = $client->dispatch('wf-123', 'stage.start', ['hello' => 'world']);

    expect($redis->lastAdd[0])->toBe('workflow:stream');
    expect($redis->lastAdd[2]['workflow_id'])->toBe('wf-123');
    expect($redis->lastAdd[2]['attempt'])->toBe(0);
    expect($redis->lastAdd[2])->not->toHaveKey('max_attempts');
    expect($id)->toBe('1677721600000-0');
});

test('workflow client allows overriding max attempts', function (): void {
    $redis = new FakeRedis();
    $client = new WorkflowClient($redis, 'workflow:stream');

    $client->dispatch('wf-override', 'stage.retry', ['hello' => 'world'], 9);

    expect($redis->lastAdd[2]['max_attempts'])->toBe(9);
});

test('example workflow uses workflow client to publish activities', function (): void {
    $redis = new FakeRedis();
    $client = new WorkflowClient($redis, 'workflow:example');
    $workflow = new ExampleWorkflow($client);

    $result = $workflow->runExample(['customer_id' => 'C123', 'max_attempts' => 6]);

    expect($result)->toBe('result-for-C123');
    expect($redis->lastAdd[2]['action'])->toBe('stage.finish');
    expect($redis->lastAdd[2]['max_attempts'])->toBe(6);
});
