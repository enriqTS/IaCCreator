# SNS to Firehose subscriptions

Connect an SNS topic to a generated Firehose delivery stream with `delivers_to`. The Firehose module owns the `firehose` subscription and an IAM role trusted by SNS with `PutRecord` and `PutRecordBatch` access limited to that stream. The topic ARN crosses into the Firehose module as an input. `raw_message_delivery` defaults to false and can be enabled to store the message without the SNS envelope.

Only standard topics are supported. The connection checks both the configured topic and the Terraform topic ARN. The Firehose stream still needs a configured delivery destination and its separate delivery role. Subscription filters, dead-letter queues, cross-account delivery, and encrypted-topic key policies remain separate. The Terraform caller needs permission to pass the subscription role to SNS.

See the AWS [Firehose subscription prerequisites](https://docs.aws.amazon.com/sns/latest/dg/prereqs-kinesis-data-firehose.html) and [subscription guide](https://docs.aws.amazon.com/sns/latest/dg/firehose-endpoints-subscribe.html).
