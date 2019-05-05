#!/usr/bin/env bash
set -e
export DONT_PROMPT_FOR_CONFIRMATION=1
echo "Deploying Image"
package aws deploy-image

echo "Deploying Task Definitions.."
package aws deploy-task-definition polaris-work-tracking-db-migrator
package aws deploy-task-definition polaris-work-tracking-service
package aws deploy-task-definition polaris-work-tracking-listener

echo "Running migrations"
package aws run-task polaris-work-tracking-db-migrator

echo "Deploying Services.."
package aws deploy-services polaris-work-tracking-service polaris.auto-scaling-group polaris-work-tracking-service polaris-work-tracking-listener
