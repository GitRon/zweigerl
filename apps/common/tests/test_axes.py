from apps.common.axes import no_client_ip


def test_no_client_ip_keeps_no_address(rf):
    request = rf.get("/", REMOTE_ADDR="192.0.2.7")

    assert no_client_ip(request) is None
