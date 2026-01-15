# Delete Task

> Deletes a task by ID.

Permanently delete a task by its ID. This action cannot be undone.


## OpenAPI

````yaml DELETE /v1/tasks/{task_id}
openapi: 3.1.0
info:
  title: Manus Integrations API
  description: API for integrating Manus into your workflow.
  version: 1.0.0
servers:
  - url: https://api.manus.ai
security:
  - bearerAuth: []
paths:
  /v1/tasks/{task_id}:
    delete:
      summary: DeleteTask
      description: Deletes a task by ID.
      operationId: openapi.v1.OpenapiOauthService.DeleteTask
      parameters:
        - name: task_id
          in: path
          required: true
          schema:
            type: string
            description: The ID of the task to delete
      responses:
        '200':
          description: Task deleted successfully.
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: string
                    description: The ID of the deleted task
                  object:
                    type: string
                    description: Always "task.deleted"
                  deleted:
                    type: boolean
                    description: Always true if successful
components:
  securitySchemes:
    bearerAuth:
      type: apiKey
      in: header
      name: API_KEY

````

---

> To find navigation and other pages in this documentation, fetch the llms.txt file at: https://open.manus.ai/docs/llms.txt