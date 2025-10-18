<?php

declare(strict_types=1);

namespace Redis\Workflow\Contracts;

interface WorkflowInterface
{
    public function getWorkflowId(): string;
}
