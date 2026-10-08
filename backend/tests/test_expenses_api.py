from decimal import Decimal

from tests.conftest import auth, register


def make_group_with_members(client, names):
    accounts = [register(client, name, f"{name.split()[0].lower()}@example.com") for name in names]
    owner_headers = auth(accounts[0]["access_token"])
    group = client.post("/api/v1/groups", headers=owner_headers, json={"name": "Trip"}).json()
    for index in range(1, len(accounts)):
        request = client.post(f"/api/v1/friends/requests/{index + 1}", headers=owner_headers).json()
        client.post(
            f"/api/v1/friends/requests/{request['id']}/accept",
            headers=auth(accounts[index]["access_token"]),
        )
        response = client.post(
            f"/api/v1/groups/{group['id']}/members",
            headers=owner_headers,
            json={"user_id": index + 1},
        )
        assert response.status_code == 201
    return accounts, group


def expense_body(title, total, payer, user_ids, split_type="EQUAL", **values):
    participants = [{"user_id": user_id, **values.get(str(user_id), {})} for user_id in user_ids]
    return {
        "title": title,
        "total_amount": total,
        "paid_by_user_id": payer,
        "split_type": split_type,
        "participants": participants,
    }


def test_create_expense_rejects_nonmember_participant_and_nonmember_payer(client):
    accounts, group = make_group_with_members(client, ["Alice Owner", "Bob Friend", "Carol Guest"])
    headers = auth(accounts[0]["access_token"])
    outsider = register(client, "David Outside", "david@example.com")
    bad_participant = client.post(
        f"/api/v1/groups/{group['id']}/expenses",
        headers=headers,
        json=expense_body("Dinner", "10.00", 1, [1, 4]),
    )
    assert bad_participant.status_code == 422
    bad_payer = client.post(
        f"/api/v1/groups/{group['id']}/expenses",
        headers=headers,
        json=expense_body("Dinner", "10.00", 4, [1, 2]),
    )
    assert bad_payer.status_code == 422
    outsider_response = client.post(
        f"/api/v1/groups/{group['id']}/expenses",
        headers=auth(outsider["access_token"]),
        json=expense_body("Dinner", "10.00", 1, [1]),
    )
    assert outsider_response.status_code == 404


def test_split_preview_and_create_preserve_decimal_total(client):
    accounts, group = make_group_with_members(client, ["Alice Owner", "Bob Friend", "Carol Friend"])
    headers = auth(accounts[0]["access_token"])
    body = expense_body("Shared meal", "10.00", 1, [1, 2, 3])
    preview = client.post(
        f"/api/v1/groups/{group['id']}/expenses/preview", headers=headers, json=body
    )
    assert preview.status_code == 200
    assert [part["amount_owed"] for part in preview.json()["allocations"]] == [
        "3.34",
        "3.33",
        "3.33",
    ]
    created = client.post(f"/api/v1/groups/{group['id']}/expenses", headers=headers, json=body)
    assert created.status_code == 201
    assert sum(
        (Decimal(part["amount_owed"]) for part in created.json()["participants"]), Decimal(0)
    ) == Decimal("10.00")


def test_group_balances_summary_and_simplification_across_two_payers(client):
    accounts, group = make_group_with_members(client, ["Alice Owner", "Bob Friend", "Carol Friend"])
    owner_headers, bob_headers = (
        auth(accounts[0]["access_token"]),
        auth(accounts[1]["access_token"]),
    )
    group_id = group["id"]
    first = client.post(
        f"/api/v1/groups/{group_id}/expenses",
        headers=owner_headers,
        json=expense_body("First meal", "6000.00", 1, [1, 2, 3]),
    )
    second = client.post(
        f"/api/v1/groups/{group_id}/expenses",
        headers=bob_headers,
        json=expense_body("Second meal", "3000.00", 2, [1, 2, 3]),
    )
    assert first.status_code == second.status_code == 201
    balances = client.get(f"/api/v1/groups/{group_id}/balances", headers=owner_headers)
    assert {line["user"]["id"]: Decimal(line["net_balance"]) for line in balances.json()} == {
        1: Decimal("3000.00"),
        2: Decimal("0.00"),
        3: Decimal("-3000.00"),
    }
    settlements = client.get(f"/api/v1/groups/{group_id}/settlements", headers=owner_headers)
    assert [
        (row["from_user"]["id"], row["to_user"]["id"], Decimal(row["amount"]))
        for row in settlements.json()
    ] == [(3, 1, Decimal("3000.00"))]
    summary = client.get(f"/api/v1/groups/{group_id}/summary", headers=owner_headers).json()
    assert Decimal(summary["total_group_spending"]) == Decimal("9000.00")
    assert Decimal(summary["current_user_total_paid"]) == Decimal("6000.00")
    assert Decimal(summary["current_user_total_share"]) == Decimal("3000.00")
    assert Decimal(summary["current_balance"]) == Decimal("3000.00")
    assert summary["unsettled_obligations"] == 1


def test_expense_edit_delete_authorization_and_pagination(client):
    accounts, group = make_group_with_members(client, ["Alice Owner", "Bob Friend"])
    owner_headers, member_headers = (
        auth(accounts[0]["access_token"]),
        auth(accounts[1]["access_token"]),
    )
    created = client.post(
        f"/api/v1/groups/{group['id']}/expenses",
        headers=owner_headers,
        json=expense_body("Lunch", "100.00", 1, [1, 2]),
    )
    expense_id = created.json()["id"]
    outsider = register(client, "Charlie Outside", "charlie@example.com")
    assert (
        client.get(
            f"/api/v1/expenses/{expense_id}", headers=auth(outsider["access_token"])
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/expenses/{expense_id}", headers=member_headers, json={"title": "Changed"}
        ).status_code
        == 403
    )
    updated = client.patch(
        f"/api/v1/expenses/{expense_id}", headers=owner_headers, json={"title": "Updated lunch"}
    )
    assert updated.status_code == 200 and updated.json()["title"] == "Updated lunch"
    page = client.get(
        f"/api/v1/groups/{group['id']}/expenses?offset=0&limit=1", headers=owner_headers
    )
    assert page.status_code == 200 and page.json()["total"] == 1 and len(page.json()["items"]) == 1
    assert (
        client.delete(f"/api/v1/expenses/{expense_id}", headers=member_headers).status_code == 403
    )
    assert client.delete(f"/api/v1/expenses/{expense_id}", headers=owner_headers).status_code == 200
    assert client.get(f"/api/v1/expenses/{expense_id}", headers=owner_headers).status_code == 404


def test_invalid_amount_and_split_values_return_validation_errors(client):
    accounts, group = make_group_with_members(client, ["Alice Owner", "Bob Friend"])
    headers = auth(accounts[0]["access_token"])
    url = f"/api/v1/groups/{group['id']}/expenses"
    assert (
        client.post(url, headers=headers, json=expense_body("Zero", "0", 1, [1])).status_code == 422
    )
    assert (
        client.post(
            url, headers=headers, json=expense_body("Negative", "-1.00", 1, [1])
        ).status_code
        == 422
    )
    exact = expense_body(
        "Bad exact",
        "10.00",
        1,
        [1, 2],
        "EXACT",
        **{"1": {"amount": "3.00"}, "2": {"amount": "6.00"}},
    )
    assert client.post(url, headers=headers, json=exact).status_code == 422


def test_empty_group_financial_views_return_zero_values(client):
    accounts, group = make_group_with_members(client, ["Alice Owner"])
    headers = auth(accounts[0]["access_token"])
    group_id = group["id"]
    history = client.get(f"/api/v1/groups/{group_id}/expenses", headers=headers).json()
    balances = client.get(f"/api/v1/groups/{group_id}/balances", headers=headers).json()
    settlements = client.get(f"/api/v1/groups/{group_id}/settlements", headers=headers).json()
    summary = client.get(f"/api/v1/groups/{group_id}/summary", headers=headers).json()
    assert history["items"] == [] and history["total"] == 0
    assert len(balances) == 1 and Decimal(balances[0]["net_balance"]) == Decimal("0.00")
    assert settlements == []
    assert Decimal(summary["total_group_spending"]) == Decimal("0.00")
    assert summary["unsettled_obligations"] == 0 and summary["recent_expenses"] == []
