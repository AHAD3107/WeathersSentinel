
# WeatherSentinel Kafka Dead-Letter Queue Runbook

## 1. Purpose

WeatherSentinel routes malformed Kafka payloads and weather messages that fail validation to a dead-letter queue (DLQ) for investigation.

## 2. Topic details

- Source topic: `weather.observations`
- Dead-letter topic: `weather.observations.dlq`
- Consumer group: `weathersentinel-consumer`
- Local broker: `localhost:9092`

## 3. Message handling

| Situation | Expected behavior |
|---|---|
| Valid weather message | Process and commit the source offset |
| Duplicate observation | Skip the duplicate and commit the source offset |
| Invalid JSON or empty payload | Publish to DLQ, then commit the source offset |
| Weather validation failure | Publish to DLQ, then commit the source offset |
| DLQ publishing failure | Do not commit the source offset; stop the worker |
| Unexpected processing failure | Roll back the database session and stop the worker |

The DLQ publisher must receive delivery confirmation before the source offset is committed.

## 4. Inspect the DLQ topic

```bash
docker exec weathersentinel-kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic weather.observations.dlq
```

## 5. Read DLQ records

```bash
docker exec -it weathersentinel-kafka \
  /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic weather.observations.dlq \
  --from-beginning
```

Stop the consumer with `Ctrl+C`.

## 6. DLQ record fields

A dead-letter record can contain:

- `dead_lettered_at`: UTC timestamp of publication
- `reason`: rejection category
- `errors`: parsing or validation details
- `original_message`: decoded message, if available
- `source`: original topic, partition and offset
- `raw_value_base64`: original raw bytes, if available

The `smoke_test` record is synthetic and was created during connectivity verification.

## 7. Troubleshooting

If the worker stops after a DLQ publishing failure:

1. Check that Docker and Kafka are running.
2. Confirm that the DLQ topic exists.
3. Check broker connectivity and worker logs.
4. Fix the underlying problem before restarting the worker.
5. Inspect the retried message.

A message may be processed more than once if the worker crashes after DLQ delivery but before committing its source offset.

## 8. Limitations

- The local DLQ has one partition and replication factor one.
- DLQ publication and source-offset commits are not atomic together.
- Automatic dead-letter replay is not implemented.
- Investigate the failure before attempting to replay a message.
