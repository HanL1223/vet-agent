def test_cl1_cl2_dashboard(client):
    summary = client.get("/api/clinic/summary").json()
    assert summary["pets_with_gaps"] == 8
    rows = client.get("/api/clinic/care-gaps?type=senior").json()
    assert {r["pet"] for r in rows} == {"Biscuit", "Nala"}


def test_cl3_rejects_unknown_filter(client):
    assert client.get("/api/clinic/care-gaps?type=grooming").status_code == 400


def test_cl4_reminder_is_recorded(client):
    key = client.get("/api/clinic/care-gaps").json()[0]["key"]
    assert client.post("/api/clinic/reminders", json={"keys": [key, "bogus"]}).json() == {"sent": 1}
    assert client.get("/api/clinic/care-gaps").json()[0]["reminded"] is True


def test_ag1_opening_raises_top_gap(client):
    items = client.get("/api/owner/conversation").json()["items"]
    assert "21 days overdue" in items[0]["texts"][-1]


def test_ag4_confirm_sends_once_to_clinic(client):
    convo = client.post("/api/owner/messages", json={"text": "Book his screening"}).json()
    proposal = convo["items"][-1]["cards"][0]
    url = f"/api/owner/proposals/{proposal['proposal_id']}/confirm"
    assert client.post(url).status_code == 200
    assert client.post(url).status_code == 409
    assert len(client.get("/api/clinic/requests").json()) == 1


def test_pr2_deidentified_use_off_by_default(client):
    consent = client.get("/api/owner/conversation").json()["consent"]
    assert consent == {"share_log": True, "deidentified_use": False}


def test_empty_message_rejected(client):
    assert client.post("/api/owner/messages", json={"text": "   "}).status_code == 400
