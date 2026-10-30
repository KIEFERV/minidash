`POST /orders` accepts an optional `scheduled_for`. Such an order is stored as `scheduled` with a
release time 30 minutes before delivery. A conditional database update moves it to `placed` once the
release time arrives. It is triggered by a background loop every 30 seconds and also whenever an
order is read or updated. Every "what time is it" question goes through one injected clock.

The layering is unchanged: `routes -> services -> repositories`. One new module, `scheduler.py`, sits
beside `main.py`.


