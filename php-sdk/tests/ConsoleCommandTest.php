<?php

declare(strict_types=1);

use Redis\Workflow\Laravel\Commands\AbstractWorkflowCommand;
use Redis\Workflow\Laravel\Commands\Laravel11RunWorkflowCommand;
use Redis\Workflow\Laravel\Commands\Laravel12RunWorkflowCommand;
use Redis\Workflow\Symfony\Command\ConfigureEnvironmentCommand;
use Redis\Workflow\Symfony\Command\RunWorkflowCommand;
use Redis\Workflow\WorkflowClient;
use Symfony\Component\Console\Tester\CommandTester;

class StubRedis
{
    public array $last = [];

    public function xAdd($stream, $id, $payload)
    {
        $this->last = [$stream, $id, $payload];
        return 'ok';
    }
}

test('laravel 11 command inherits the abstract workflow command helpers', function (): void {
    $command = new Laravel11RunWorkflowCommand(new WorkflowClient(new StubRedis()));
    $reflection = new ReflectionClass($command);
    expect($reflection->isSubclassOf(AbstractWorkflowCommand::class))->toBeTrue();
    $property = $reflection->getProperty('signature');
    $property->setAccessible(true);
    expect($property->getValue($command))->toContain('workflow:run');
});

test('laravel 12 command exposes optional customer parameter', function (): void {
    $command = new Laravel12RunWorkflowCommand(new WorkflowClient(new StubRedis()));
    $signature = (new ReflectionClass($command))->getProperty('signature')->getValue($command);

    expect($signature)->toContain('--customer');
});

test('symfony console command renders workflow output', function (): void {
    $client = new WorkflowClient(new StubRedis());
    $command = new RunWorkflowCommand($client);
    $tester = new CommandTester($command);
    $tester->execute(['customer' => 'A1']);

    expect($tester->getDisplay())->toContain('Workflow finished with result');
});

test('symfony environment command writes defaults', function (): void {
    $tmp = sys_get_temp_dir().'/workflow-symfony-'.uniqid();
    mkdir($tmp);
    file_put_contents($tmp.'/.env', "APP_ENV=dev\n");

    $command = new ConfigureEnvironmentCommand();
    $tester = new CommandTester($command);
    $tester->execute(['--project' => $tmp]);

    expect(file_get_contents($tmp.'/.env'))->toContain('WORKFLOW_REDIS_URL=');
});
