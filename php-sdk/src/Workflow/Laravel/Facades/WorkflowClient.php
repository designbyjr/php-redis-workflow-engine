<?php

declare(strict_types=1);

namespace Redis\Workflow\Laravel\Facades;

use Illuminate\Support\Facades\Facade;
use Redis\Workflow\WorkflowClient as BaseClient;

class WorkflowClient extends Facade
{
    protected static function getFacadeAccessor(): string
    {
        return BaseClient::class;
    }
}
