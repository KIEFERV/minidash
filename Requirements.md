

Customers can place an order now and choose a later delivery time. The order is held, then handed
to the restaurant 30 minutes before the delivery time. Until then the customer can cancel it.

**1.1** Where a create-order request includes `scheduled_for`, the API shall create the order with status `scheduled` and respond `201`.
- **1.2** When a scheduled order is created, the API shall record its delivery time and a release time 30 minutes earlier, and shall return `scheduled_for` with `released_at` set to null.
- **1.3** When a create-order request omits `scheduled_for` or sets it to null, the API shall create the order with status `placed` and shall require the restaurant to be open at that moment.
- **1.4** The API shall compute a scheduled order's total from the menu prices at the time the order is created, exactly as it does for immediate orders.
- **1.5** When `scheduled_for` carries a UTC offset or a trailing `Z`, the API shall convert it to server-local time before applying any other rule.
- **1.6** When `scheduled_for` includes fractional seconds, the API shall ignore the fractional part.
- **1.7** While the restaurant is closed at the moment of ordering, the API shall accept a scheduled order whose delivery time falls within the restaurant's opening hours.

*2.1** If `scheduled_for` is less than 45 minutes after the current time (including any time in the past), then the API shall reject the request with `422` and the detail `Please enter a valid time`.
- **2.2** If `scheduled_for` is more than 7 days after the current time, then the API shall reject the request with `422` and the detail `Please enter a valid time`.
- **2.3** The API shall accept a delivery time that is exactly 45 minutes, or exactly 7 days, after the current time.
- **2.4** If `scheduled_for` is not a complete ISO 8601 date and time (for example empty, plain words, or a date without a time), then the API shall reject the request with `422` and the detail `Please enter a valid time`.
- **2.5** If the delivery time is outside the allowed window and the restaurant would also be closed at that time, then the API shall report `Please enter a valid time` rather than the closed-restaurant message.

*3.1** If the restaurant is closed at the delivery time, then the API shall reject the request with `409` and a detail that names the restaurant, says it is closed at the requested delivery time, and gives its opening hours.
- **3.2** The API shall treat a restaurant as open at its opening time and closed at its closing time.
- **3.3** Where a restaurant's closing time is earlier than its opening time, the API shall treat the restaurant as open overnight, across midnight.
- **3.4** Where a restaurant's opening time equals its closing time, the API shall treat the restaurant as open 24 hours.

**4.1** While a scheduled order's release time has not arrived, the API shall report its status as `scheduled`.
- **4.2** When the current time reaches an order's release time, the API shall change its status from `scheduled` to `placed` and record `released_at`.
- **4.3** The API shall release each scheduled order exactly once.
- **4.4** While the application is running with the background job enabled, the API shall look for due scheduled orders every 30 seconds and release them.
- **4.5** When the application starts, the API shall release every scheduled order whose release time has already passed.
- **4.6** When a client reads or updates an order whose release time has arrived, the API shall release it before responding, so the response does not depend on when the background job last ran.
- **4.7** If a background release run fails, then the API shall log the failure and try again at the next interval.
- **4.8** While a released order is `placed`, the API shall apply the normal order lifecycle to it (confirmed, preparing, out for delivery, delivered).

 **5.1** When a client requests status `cancelled` for an order that is `scheduled`, the API shall set its status to `cancelled`.
- **5.2** If a scheduled order has been cancelled, then the API shall never release it and shall leave `released_at` empty.
- **5.3** If a client requests any status other than `cancelled` for an order that is `scheduled`, then the API shall reject the request with `409` and leave the order unchanged.
- **5.4** If a client requests status `placed` for an order that is `scheduled`, then the API shall reject the request with `409` and a detail explaining that release is automatic.
- **5.5** If a client requests status `scheduled` for any order, then the API shall reject the request with `409`.
- **5.6** While a released order is `placed` or `confirmed`, the API shall allow the client to cancel it (the existing lifecycle rule).
- **5.7** If an order's status was changed by another request between the API reading it and updating it, then the API shall reject the update with `409` instead of overwriting the change.

**6.1** The API shall obtain the current time only from an injected clock, which defaults to server-local time.
- **6.2** The API shall use that same clock for the delivery-time window, opening-hours checks, `created_at`, `released_at` and the background release job.
- **6.3** Where the release interval is set to none, the API shall not start the background release job.
- **6.4** When the application shuts down, the API shall stop the background release job.

**7.1** When the application starts against a database created before this feature, the API shall add the scheduling columns that are missing.
- **7.2** When the application starts against such a database, the API shall change every order with status `pending` to `placed`.
- **7.3** When the upgrade runs more than once, the API shall leave the data unchanged after the first run.
- **7.4** When the application starts against a database that already contains restaurants, the API shall not seed them again.

OUT OF SCOPE

**Authentication and authorisation**, including who may cancel an order.
- **Notifying anyone.** "Released to the restaurant" is a status change only. There are no push messages, emails or SMS, and no restaurant-facing endpoint or list of incoming orders.
- **Changing a scheduled order.** Editing its time, items or address, or rescheduling, is not supported. The customer cancels and orders again.
- **Restaurant-side accept or reject**, and any change to the confirm, prepare, deliver steps.
- **Opening hours at release time.** Only the delivery time is checked against opening hours. An order for 11:10 from a restaurant that opens at 11:00 is released at 10:40, while it is closed.
- **Preparation time.** `avg_prep_minutes` plays no part in release timing or delivery estimates.
- **Time zones and daylight saving.** There is one server-local time; per-restaurant or per-customer zones are not handled, and ambiguous local times at clock changes are not special-cased.
- **Holidays, special opening days and recurring (repeat) orders.**
- **Payments, refunds and cancellation fees.**
- **A dedicated cancel endpoint.** Cancelling uses the existing `PATCH /orders/{id}/status`.
- **Configuring the limits.** The 45 minutes, 7 days, 30-minute release lead and 30-second job interval are not settable through environment variables or the API.
- **Several server processes or machines.** The release is written to be safe if two runners overlap, but running more than one process is neither designed for nor tested.
- **A customer-facing web page.** The feature is available through the API and its `/docs` page only.
- **Exposing the planned release time** (`release_at`) in API responses. It is stored and used internally.
