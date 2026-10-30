# Microservices and CQRS

Reference for NestJS microservice transports, message and event patterns, hybrid applications, client proxies, and the `@nestjs/cqrs` module. Verified against `@nestjs/microservices` 12.3.2, `@nestjs/cqrs` 12.1.2 and the NestJS documentation sources (2026-10). Architecture trade-offs between services belong to microservices-expert and system-design-expert.

## 1. Transports

`Transport` enum values in `@nestjs/microservices`: `TCP`, `REDIS`, `NATS`, `MQTT`, `GRPC`, `RMQ`, `KAFKA`. Custom transports are possible through a custom transport strategy.

| Transport | Typical use | Notes |
|---|---|---|
| TCP (default) | Internal service-to-service calls, tests | Supports TLS through `tlsOptions`; protect with network policy and TLS outside private networks |
| Redis | Lightweight pub/sub | Request-response uses two logical channels created by Nest |
| NATS | Low-latency messaging | v12 targets NATS v3: replace the `nats` package with `@nats-io/transport-node`; `StringCodec` and `JSONCodec` helpers are gone; custom deserializers receive the full NATS message and should read `msg.json()` |
| MQTT | IoT, many small clients | |
| RabbitMQ (`RMQ`) | Work queues, routing, acknowledgements | |
| Kafka | Log-based streaming, replay, consumer groups; regex patterns for `@MessagePattern` and `@EventPattern` in v12 | |
| gRPC | Typed RPC with `.proto` contracts | v12 adds `GrpcExceptionFilter` and status-specific exceptions mapping to proper gRPC status codes |

Request-response needs a response channel; some transports provide it natively (NATS), for others Nest creates it, adding overhead. If a flow does not need a reply, prefer events.

## 2. A microservice

```ts
// main.ts of a standalone microservice
import { NestFactory } from '@nestjs/core';
import { type MicroserviceOptions, Transport } from '@nestjs/microservices';
import { AppModule } from './app.module.js';

const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
  transport: Transport.TCP,
  options: { host: '127.0.0.1', port: 4001 },
});
app.enableShutdownHooks();
await app.listen();
```

Handlers:

```ts
import { Controller } from '@nestjs/common';
import { EventPattern, MessagePattern, Payload } from '@nestjs/microservices';

@Controller()
export class MathController {
  @MessagePattern({ cmd: 'sum' })           // request-response
  sum(@Payload() data: number[]): number {
    return data.reduce((a, b) => a + b, 0);
  }

  @EventPattern('user_created')             // fire-and-forget event
  handleUserCreated(@Payload() data: { id: string }): void {
    // idempotent processing
  }
}
```

- A pattern is any serializable value (string or object). Message patterns return a value, observable or promise; event patterns do not respond.
- Validation pipes work on `@Payload()`; the Standard Schema pipe supports `@Payload({ schema })` as well.
- Throw `RpcException` for errors that must travel back to the caller. HTTP exceptions are not translated automatically on RPC transports.
- Authorization on RPC: guards also run for microservice handlers; the transport is not an authentication boundary, so protect the network and verify caller identity in messages when needed.

## 3. Clients

```ts
import { Module } from '@nestjs/common';
import { ClientsModule, Transport } from '@nestjs/microservices';

@Module({
  imports: [
    ClientsModule.register([
      { name: 'MATH_SERVICE', transport: Transport.TCP, options: { host: '127.0.0.1', port: 4001 } },
    ]),
  ],
})
export class GatewayModule {}
```

```ts
import { Inject, Injectable } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom, timeout } from 'rxjs';

@Injectable()
export class MathClient {
  constructor(@Inject('MATH_SERVICE') private readonly client: ClientProxy) {}

  sum(numbers: number[]): Promise<number> {
    return firstValueFrom(this.client.send<number, number[]>({ cmd: 'sum' }, numbers).pipe(timeout(3000)));
  }

  announce(id: string): void {
    this.client.emit('user_created', { id }); // hot observable: delivery starts without a subscriber
  }
}
```

- `send()` returns a cold `Observable`; nothing is sent until it is subscribed. Convert with `firstValueFrom` and always apply `timeout`. `emit()` returns a hot `Observable`: the event is delivered whether or not you subscribe; subscribe or convert it when you need to observe delivery errors.
- Build clients from configuration with `ClientsModule.registerAsync()` or `ClientProxyFactory.create()` in a custom provider.
- A client connects lazily; call `await client.connect()` at startup to fail fast, and `client.close()` on shutdown. Subscribe to `client.status` for connection state.
- With the TCP transport (12.1.1+), listeners registered with the client's `on()` stay registered until `close()` and are reattached after reconnect; do not register them repeatedly.

## 4. Hybrid applications

Serve HTTP and a transport from one process:

```ts
const app = await NestFactory.create(AppModule);
app.connectMicroservice<MicroserviceOptions>({
  transport: Transport.RMQ,
  options: { urls: [process.env.RABBITMQ_URL!], queue: 'orders', queueOptions: { durable: true } },
});
await app.startAllMicroservices();
await app.listen(process.env.PORT ?? 3000);
```

Global guards and interceptors of the application run on the message handlers of a hybrid app only when `connectMicroservice()` receives `{ inheritAppConfig: true }` as its second argument; without it, a global authorization guard does not protect the message handlers. Register enhancers through `APP_*` tokens in modules to control both contexts deliberately.

## 5. Reliability rules

- At-least-once delivery is the norm: make handlers idempotent (idempotency key, upsert, dedupe table).
- Ack after processing, not before, for brokers that support it; configure dead-letter queues or topics.
- Keep payloads small and versioned; add a schema version or use a typed contract (protobuf for gRPC and Kafka schemas).
- Propagate correlation or trace ids through message headers; with `@nestjs/observe` or OpenTelemetry forward the trace id on the channel the transport offers (Kafka header, NATS header, field in the TCP payload).
- Time out every request-response call and define the failure behavior (retry with backoff, circuit breaker, fallback).
- Test with the real broker in a container for wiring, and with plain handler tests for logic.

## 6. CQRS with @nestjs/cqrs

Install `@nestjs/cqrs` and import `CqrsModule.forRoot()`. `forRootAsync()` accepts options from a factory. Options include `commandPublisher`, `eventPublisher`, `queryPublisher`, `unhandledExceptionPublisher`, `eventIdProvider` and `rethrowUnhandled` (default `false`, so exceptions from event handlers and sagas are published to the `UnhandledExceptionBus`).

Command and handler:

```ts
import { Command, CommandBus, CommandHandler, type ICommandHandler } from '@nestjs/cqrs';

export class KillDragonCommand extends Command<{ actionId: string }> {
  constructor(public readonly heroId: string, public readonly dragonId: string) {
    super();
  }
}

@CommandHandler(KillDragonCommand)
export class KillDragonHandler implements ICommandHandler<KillDragonCommand> {
  constructor(private readonly repository: HeroesRepository) {}

  async execute(command: KillDragonCommand) {
    const hero = await this.repository.findOneById(command.heroId);
    hero.killEnemy(command.dragonId);
    await this.repository.save(hero);
    return { actionId: crypto.randomUUID() };
  }
}

// caller: const { actionId } = await this.commandBus.execute(new KillDragonCommand(heroId, dragonId));
```

- Extending `Command<T>` (and `Query<T>`) is optional and gives `execute()` an inferred return type.
- Queries: `@QueryHandler(GetHeroQuery)` and `IQueryHandler`, dispatched with `QueryBus.execute()`.
- Events: aggregates extend `AggregateRoot` and call `apply(event)`; connect them to the bus with `EventPublisher.mergeObjectContext(entity)` and call `commit()`; or publish directly with `EventBus.publish(event)`. `@EventsHandler(Event)` classes implement `IEventHandler` and may be many per event.
- Sagas are properties decorated with `@Saga()` returning an RxJS `Observable` of commands (`events$.pipe(ofType(HeroKilledDragonEvent), map(...))`). They run in memory; for workflows that must survive restarts, use the durable sagas approach in the docs or an external workflow engine.
- Register every handler and saga class as a provider of a module.
- Event handlers run outside the HTTP request: exception filters do not catch their errors, so handle them with `try/catch`, compensating events or the unhandled exception bus. Command handler errors do reach exception filters.
- Use CQRS where it removes coupling (separate read models, event-driven side effects). For simple CRUD a service layer is enough, and CQRS adds indirection.
