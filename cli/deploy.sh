#!/usr/bin/env bash
echo "Deploying Image"
package aws deploy-image

echo "Deploying Task Definitions.."
package aws deploy-task-definition polaris-work-tracking-db-migrator
package aws deploy-task-definition polaris-work-tracking-service
package aws deploy-task-definition polaris-work-tracking-listener
package aws deploy-task-definition polaris-work-tracking-sync-agent

