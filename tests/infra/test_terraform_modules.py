from pathlib import Path

IAM_BINDING_MODULE = Path("infra/terraform/modules/base/iam_binding/main.tf")


def test_service_account_iam_bindings_use_static_instance_keys() -> None:
    """New identity resources must be plannable before their IDs exist."""
    source = IAM_BINDING_MODULE.read_text()

    assert "for index, binding in var.service_account_bindings : index => binding" in source
