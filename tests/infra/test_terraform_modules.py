import re
from pathlib import Path

IAM_BINDING_MODULE = Path("infra/terraform/modules/base/iam_binding/main.tf")
GITHUB_FEDERATION_MODULE = Path(
    "infra/terraform/modules/foundations/github_federation/main.tf"
)


def test_service_account_iam_bindings_use_static_instance_keys() -> None:
    """New identity resources must be plannable before their IDs exist."""
    source = IAM_BINDING_MODULE.read_text()

    assert "for index, binding in var.service_account_bindings : index => binding" in source


def test_main_branch_workload_identities_are_matched_by_a_mapped_principal() -> None:
    """WIF branch restrictions belong in the principal identifier, not IAM CEL."""
    source = GITHUB_FEDERATION_MODULE.read_text()

    assert re.search(
        r'"attribute\.repository_ref"\s+=\s+"assertion\.repository \+ \\"\:\\" \+ assertion\.ref"',
        source,
    )
    protected_branch_attribute = (
        "attribute.repository_ref/${var.github_repository}:refs/heads/${var.github_branch}"
    )
    assert protected_branch_attribute in source
    assert "attribute.ref ==" not in source
