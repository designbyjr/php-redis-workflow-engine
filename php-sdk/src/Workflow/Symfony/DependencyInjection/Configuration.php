<?php

declare(strict_types=1);

namespace Redis\Workflow\Symfony\DependencyInjection;

use Symfony\Component\Config\Definition\Builder\TreeBuilder;
use Symfony\Component\Config\Definition\ConfigurationInterface;

class Configuration implements ConfigurationInterface
{
    public function getConfigTreeBuilder(): TreeBuilder
    {
        $treeBuilder = new TreeBuilder('redis_workflow');
        $rootNode = $treeBuilder->getRootNode();

        $rootNode
            ->children()
                ->scalarNode('host')->defaultValue('127.0.0.1')->end()
                ->integerNode('port')->defaultValue(6379)->end()
                ->floatNode('timeout')->defaultValue(1.5)->end()
                ->integerNode('database')->defaultValue(0)->end()
                ->scalarNode('password')->defaultNull()->end()
                ->scalarNode('stream')->defaultValue('workflow:stream')->end()
            ->end();

        return $treeBuilder;
    }
}
