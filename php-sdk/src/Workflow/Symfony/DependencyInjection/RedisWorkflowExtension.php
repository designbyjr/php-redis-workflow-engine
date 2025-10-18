<?php

declare(strict_types=1);

namespace Redis\Workflow\Symfony\DependencyInjection;

use Redis;
use Redis\Workflow\Symfony\Command\ConfigureEnvironmentCommand;
use Redis\Workflow\Symfony\Command\RunWorkflowCommand;
use Redis\Workflow\WorkflowClient;
use Symfony\Component\DependencyInjection\ContainerBuilder;
use Symfony\Component\DependencyInjection\Definition;
use Symfony\Component\DependencyInjection\Reference;
use Symfony\Component\HttpKernel\DependencyInjection\Extension;

class RedisWorkflowExtension extends Extension
{
    public function load(array $configs, ContainerBuilder $container): void
    {
        $configuration = new Configuration();
        $config = $this->processConfiguration($configuration, $configs);

        $container->setParameter('redis_workflow.config', $config);

        $redisDefinition = new Definition(Redis::class);
        $redisDefinition->setFactory([self::class, 'createRedisClient']);
        $redisDefinition->setArguments([$config]);
        $redisDefinition->setPublic(false);

        $container->setDefinition('redis_workflow.redis_client', $redisDefinition);

        $workflowClientDefinition = new Definition(WorkflowClient::class);
        $workflowClientDefinition->setArguments([
            new Reference('redis_workflow.redis_client'),
            $config['stream'],
        ]);

        $container->setDefinition(WorkflowClient::class, $workflowClientDefinition);

        $commandDefinition = new Definition(RunWorkflowCommand::class);
        $commandDefinition->setArguments([
            new Reference(WorkflowClient::class),
        ]);
        $commandDefinition->addTag('console.command');
        $container->setDefinition('redis_workflow.console.run_workflow', $commandDefinition);

        $envCommand = new Definition(ConfigureEnvironmentCommand::class);
        $envCommand->addTag('console.command');
        $container->setDefinition('redis_workflow.console.env', $envCommand);
    }

    public static function createRedisClient(array $config): Redis
    {
        $client = new Redis();
        $client->connect($config['host'], (int) $config['port'], (float) $config['timeout']);

        if (!empty($config['password'])) {
            $client->auth($config['password']);
        }

        if (!empty($config['database'])) {
            $client->select((int) $config['database']);
        }

        return $client;
    }
}
