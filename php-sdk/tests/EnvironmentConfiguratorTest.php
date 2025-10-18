<?php

use Redis\Workflow\Env\EnvironmentConfigurator;

it('ensures env files receive workflow defaults', function () {
    $tmp = sys_get_temp_dir().'/workflow-env-'.uniqid();
    mkdir($tmp);

    file_put_contents($tmp.'/.env', "APP_ENV=testing\nREDIS_HOST=localhost\n");

    $configurator = new EnvironmentConfigurator();
    $updated = $configurator->ensure($tmp);

    expect($updated)->toContain($tmp.'/.env');

    $contents = file_get_contents($tmp.'/.env');
    expect($contents)->toContain('WORKFLOW_REDIS_URL=');
    expect($contents)->toContain('WORKFLOW_POSTGRES_DSN=');
    expect($contents)->toContain('WORKFLOW_POLL_INTERVAL=');
    expect($contents)->toContain('WORKFLOW_MAX_RETRY_ATTEMPTS=');
});
