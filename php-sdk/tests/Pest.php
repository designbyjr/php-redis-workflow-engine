<?php

declare(strict_types=1);

expect()->extend('toBeUuid', function (): void {
    expect($this->value)->toMatch('/^[a-f0-9-]{36}$/');
});
