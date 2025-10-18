<?php

declare(strict_types=1);

namespace Redis\Workflow\Symfony;

use Symfony\Component\HttpKernel\Bundle\Bundle;
use Redis\Workflow\Symfony\DependencyInjection\RedisWorkflowExtension;

class RedisWorkflowBundle extends Bundle
{
    public function getContainerExtension(): RedisWorkflowExtension
    {
        return new RedisWorkflowExtension();
    }
}
