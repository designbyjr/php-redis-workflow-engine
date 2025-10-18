<?php

declare(strict_types=1);

namespace Redis\Workflow\Attributes;

use Attribute;

#[Attribute(Attribute::TARGET_METHOD)]
final class WorkflowMethod
{
    public function __construct(
        public readonly ?string $name = null,
        public readonly int $timeoutSeconds = 0
    ) {
    }
}
