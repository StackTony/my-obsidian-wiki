---
title: RabbitMQ Exchanges RoutingKeys Bindings详解
credibility: low
created: 2026-05-26
---

> [!info] Info
> Give LavinMQ a shot. Your queues will thank you!

### RabbitMQ routing relies on exchanges, bindings, and queues. But how do they work together? This guide explains these core concepts, the four primary exchange types, and how to handle undeliverable messages using Dead Lettering.

Messages are not published directly to a queue. Instead, the producer sends messages to an exchange. Exchanges are message-routing agents defined by the virtual host in RabbitMQ. An exchange is responsible for routing messages to different queues using header attributes, bindings, and routing keys.

A **binding** is a "link" that you set up to bind a queue to an exchange.

The **routing key** is a message attribute that the exchange uses to determine how to route the message to queues (depending on exchange type).

Exchanges, connections, and queues can be configured with parameters such as durable, temporary, and auto-delete upon creation. Durable exchanges survive server restarts and last until they are explicitly deleted. Temporary exchanges exist until RabbitMQ is shut down. Auto-deleted exchanges are removed once the last bound object is unbound from the exchange.

In RabbitMQ, there are four different types of exchanges that route the message differently using different parameters and binding setups. Clients can create their own exchanges or use the predefined default exchanges created when the server starts for the first time.

## Standard RabbitMQ message flow

1. The producer publishes a message to the exchange.
2. The exchange receives the message and is now responsible for the routing of the message.
3. Binding must be set up between the queue and the exchange. In this case, we have bindings to two different queues from the exchange. The exchange routes the message into the queues.
4. The messages stay in the queue until they are handled by a consumer.
5. The consumer handles the message.

![Exchanges Bindings Routing Keys](https://www.cloudamqp.com/img/blog/exchanges-bidings-routing-keys.svg "Exchanges Bindings Routing Keys")

If you are not familiar with RabbitMQ and message queueing, read [RabbitMQ for beginners - what is RabbitMQ?](https://www.cloudamqp.com/blog/part1-rabbitmq-for-beginners-what-is-rabbitmq.html) before moving on to exchanges, routing keys, headers, and bindings.

## Exchange types

## Direct Exchange

A direct exchange delivers messages to queues based on a message routing key. The routing key is a message attribute added to the message header by the producer. Think of the routing key as an "address" that the exchange is using to decide how to route the message. **A message goes to the queue(s) with the binding key that exactly matches the routing key of the message.**

The direct exchange type is useful to distinguish messages published to the same exchange using a simple string identifier

The default exchange for AMQP brokers must be "amq.direct".

Imagine that queue A (create\_pdf\_queue) in the image below (Direct Exchange Figure) is bound to a direct exchange (pdf\_events) with the binding key pdf\_create. When a new message with routing key pdf\_create arrives at the direct exchange, the exchange routes it to the queue where the binding\_key = routing\_key, in the case of queue A (create\_pdf\_queue).

#### Scenario 1

- Exchange: pdf\_events
- Queue A: create\_pdf\_queue
- Binding key between exchange (pdf\_events) and Queue A (create\_pdf\_queue): pdf\_create

#### Scenario 2

- Exchange: pdf\_events
- Queue B: pdf\_log\_queue
- Binding key between exchange (pdf\_events) and Queue B (pdf\_log\_queue): pdf\_log

#### Example

Example: A message with routing key pdf\_log is sent to the exchange pdf\_events. The message is routed to pdf\_log\_queue because the routing key (pdf\_log) matches the binding key (pdf\_log).

If the message routing key does not match any binding key, the message is discarded.

![rabbitmq exchange](https://www.cloudamqp.com/img/blog/direct-exchange.svg "rabbitmq exchange")

Direct Exchange: A message is routed to queues whose binding key exactly matches the message's routing key.

## Default exchange

The default exchange is a predeclared, unnamed direct exchange, typically referred to as an empty string. When you use a default exchange, your message is delivered to the queue with a name equal to the routing key of the message. Every queue is automatically bound to the default exchange with a routing key equal to the queue name.

## Topic Exchange

Topic exchanges route messages to queues based on wildcard matches between the routing key and the routing pattern, which is specified by the queue binding. Messages are routed to one or many queues based on a match between a message routing key and this pattern.

The routing key must be a list of words, delimited by a period (.). Examples include agreements.us and agreements.eu.stockholm, which identify agreements configured for a company with offices in multiple locations. The routing patterns may contain an asterisk (“\*”) to match a word in a specific position of the routing key (e.g., a routing pattern of "agreements.\*.\*.b.\*" only match routing keys where the first word is "agreements" and the fourth word is "b"). A pound symbol (“#”) indicates a match of zero or more words (e.g., a routing pattern of "agreements.eu.berlin.#" matches any routing keys beginning with "agreements.eu.berlin").

Consumers indicate which topics they are interested in (e.g., subscribing to a feed for a specific tag). The consumer creates a queue and binds it to the exchange using a specified routing pattern. All messages with a routing key that matches the routing pattern are routed to the queue and remain there until the consumer consumes them.

The default exchange AMQP broker must use the "amq.topic" topic exchange.

#### Scenario 1

The image on the right shows an example in which consumer A is interested in all agreements in Berlin.

- Exchange: agreements
- Queue A: berlin\_agreements
- Routing pattern between exchange (agreements) and Queue A (berlin\_agreements): agreements.eu.berlin.#
- Example of message routing key that matches: agreements.eu.berlin and agreements.eu.berlin.store

#### Scenario 2

Consumer B is interested in all the agreements.

- Exchange: agreements
- Queue B: all\_agreements
- Routing pattern between exchange (agreements) and Queue B (all\_agreements): agreements.#
- Example of message routing key that matches: agreements.eu.berlin and agreements.us

![rabbitmq topic exchange](https://www.cloudamqp.com/img/blog/topic-exchange.svg "rabbitmq topic exchange")

Topic Exchange: Messages are routed to one or many queues based on a match between a message routing key and the routing pattern.

#### Scenario 3

Consumer C is interested in all agreements for European head stores.

- Exchange: agreements
- Queue C: store\_agreements
- Routing pattern between exchange (agreements) and Queue C (store\_agreements): agreements.eu.\*.store
- Example of message routing keys that will match: agreements.eu.berlin.store and agreements.eu.stockholm.store

#### Example

A message with routing key *agreements.eu.berlin* is sent to the agreements exchange. The messages are routed to the queue *berlin\_agreements* because the routing pattern of "agreements.eu.berlin.#" matches the routing keys beginning with "agreements.eu.berlin". The message is also routed to the queue *all\_agreements* because the routing key (agreements.eu.berlin) matches the routing pattern (agreements.#).

## Fanout Exchange

A fanout exchange copies and routes a received message to all queues that are bound to it, regardless of routing keys or pattern matching, as with direct and topic exchanges. The provided keys will be ignored.

Fanout exchanges can be useful when the same message needs to be sent to one or more queues, with consumers that may process it differently.

The image to the right (Fanout Exchange) shows an example in which a message received by the exchange is copied and routed to all three queues bound to it. It could be sport or weather updates that should be sent out to each connected mobile device when something happens, for instance.

The default exchange AMQP brokers must provide for the topic exchange is "amq.fanout".

![rabbitmq fanout exchange](https://www.cloudamqp.com/img/blog/fanout-exchange.svg "rabbitmq fanout exchange")

Fanout Exchange: The received message is routed to all queues that are bound to the exchange.

#### Scenario 1

- Exchange: sport\_news
- Queue A: Mobile client queue A
- Binding: Binding between the exchange (sport\_news) and Queue A (Mobile client queue A)

#### Example

A message is sent to the exchange sport\_news. The message is routed to all queues (Queue A, Queue B, Queue C) because all queues are bound to the exchange. Provided routing keys are ignored.

## Headers Exchange

A header exchange routes messages based on arguments containing headers and optional values. Header exchanges are very similar to topic exchanges, but route messages based on header values rather than routing keys. A message matches if the value of the header equals the value specified upon binding.

A special argument named "x-match", added in the binding between exchange and queue, specifies if all headers must match or just one. Either any common header between the message and the binding counts as a match, or all the headers referenced in the binding need to be present in the message for it to match. The "x-match" property can have two different values: "any" or "all", where "all" is the default value. A value of "all" means all header pairs (key, value) must match, while a value of "any" means at least one of the header pairs must match. Headers can be constructed using a wider range of data types, integer or hash, for example, instead of a string. The headers exchange type (used with the binding argument "any") is useful for directing messages that contain a subset of known (unordered) criteria.

The default exchange AMQP brokers must provide for the topic exchange is "amq.headers".

#### Example

- Exchange: Binding to Queue A with arguments (key = value): format = pdf, type = report, x-match = all
- Exchange: Binding to Queue B with arguments (key = value): format = pdf, type = log, x-match = any
- Exchange: Binding to Queue C with arguments (key = value): format = zip, type = report, x-match = all

#### Scenario 1

Message 1 is published to the exchange with header arguments (key = value): "format = pdf", "type = report".

Message 1 is delivered to Queue A because all key/value pairs match, and Queue B since "format = pdf" is a match (binding rule set to "x-match =any").

#### Scenario 2

Message 2 is published to the exchange with header arguments of (key = value): "format = pdf".

Message 2 is only delivered to Queue B. Because the binding of Queue A requires both "format = pdf" and "type = report" while Queue B is configured to match any key-value pair (x-match = any) as long as either "format = pdf" or "type = log" is present.

![rabbitmq Headers exchange](https://www.cloudamqp.com/img/blog/rabbitmq-headers-exchange.svg "rabbitmq headers exchange")

Example of Headers Exchange. Routes messages to queues that are bound using arguments (key and value) in the amq. headers attribute.

#### Scenario 3

Message 3 is published to the exchange with header arguments of (key = value): "format = zip", "type = log".

Message 3 is delivered to Queue B since its binding indicates that it accepts messages with the key-value pair "type = log", it doesn't mind that "format = zip" since "x-match = any".

Queue C doesn't receive any of the messages since its binding is configured to match all of the headers ("x-match = all") with "format = zip", "type = pdf". No message in this example lives up to these criterias.

It's worth noting that in a header exchange, the actual order of the key-value pairs in the message is irrelevant.

## Dead Letter Exchange

If no matching queue can be found for the message, the message is silently dropped. RabbitMQ provides an AMQP extension known as the "Dead Letter Exchange", which provides the functionality to capture messages that are not deliverable.

Please email us at [contact@cloudamqp.com](mailto:contact@cloudamqp.com) if you have any suggestions about missing content or other feedback.