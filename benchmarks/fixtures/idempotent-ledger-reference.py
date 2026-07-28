def process_idempotent_transfers(initial_balances, events):
    if not isinstance(initial_balances, dict):
        raise ValueError("initial_balances must be a dictionary")
    balances = {}
    for account, balance in initial_balances.items():
        if (
            not isinstance(account, str)
            or not account
            or isinstance(balance, bool)
            or not isinstance(balance, int)
            or balance < 0
        ):
            raise ValueError("initial balances must map account names to non-negative integers")
        balances[account] = balance
    if not isinstance(events, list):
        raise ValueError("events must be a list")

    seen = {}
    results = []
    required_fields = {"id", "from", "to", "amount"}
    for event in events:
        if not isinstance(event, dict) or set(event) != required_fields:
            raise ValueError("events must contain exactly id, from, to, and amount")
        event_id = event["id"]
        source = event["from"]
        destination = event["to"]
        amount = event["amount"]
        if (
            not isinstance(event_id, str)
            or not event_id
            or not isinstance(source, str)
            or not source
            or not isinstance(destination, str)
            or not destination
            or source == destination
            or isinstance(amount, bool)
            or not isinstance(amount, int)
            or amount <= 0
        ):
            raise ValueError("invalid transfer event")

        signature = (source, destination, amount)
        if event_id in seen:
            original_signature, cached_result = seen[event_id]
            if signature != original_signature:
                raise ValueError("idempotency key reused with a different payload")
            results.append(dict(cached_result))
            continue

        source_balance = balances.get(source, 0)
        destination_balance = balances.get(destination, 0)
        if source_balance < amount:
            status = "rejected"
        else:
            status = "applied"
            source_balance -= amount
            destination_balance += amount
            balances[source] = source_balance
            balances[destination] = destination_balance
        result = {
            "id": event_id,
            "status": status,
            "from_balance": source_balance,
            "to_balance": destination_balance,
        }
        seen[event_id] = (signature, result)
        results.append(dict(result))

    return {"results": results, "balances": balances}
