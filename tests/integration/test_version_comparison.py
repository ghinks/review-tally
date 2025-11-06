"""Integration test comparing local and released versions of review-tally."""

import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

# Constants
FLOAT_TOLERANCE = 0.01  # Tolerance for floating point comparisons


def parse_tabulated_output(output: str) -> dict[str, dict[str, Any]]:
    """
    Parse tabulated output into a dictionary of user stats.

    Args:
        output: The raw output from review-tally command

    Returns:
        Dictionary mapping username to their stats
        Example: {'user1': {'reviews': 10, 'comments': 25, ...}, ...}

    """
    lines = output.strip().split("\n")
    user_stats: dict[str, dict[str, Any]] = {}

    # Find the header line to extract column names
    header_line = None
    data_start_idx = 0

    for idx, line in enumerate(lines):
        # Skip empty lines
        if not line.strip():
            continue

        # Look for separator line (contains dashes/hyphens)
        if re.match(r"^[\s\-+|]+$", line) and idx > 0:
            header_line = lines[idx - 1]
            data_start_idx = idx + 1
            break

    if header_line is None:
        # If no separator found, try to parse first non-empty line as header
        for idx, line in enumerate(lines):
            if line.strip():
                header_line = line
                data_start_idx = idx + 1
                break

    if header_line is None:
        return user_stats

    # Parse header to get column names
    # Split by multiple spaces or pipe characters
    headers = [
        h.strip().lower().replace(" ", "-")
        for h in re.split(r"\s{2,}|\|", header_line)
        if h.strip()
    ]

    # Parse data rows
    for line in lines[data_start_idx:]:
        # Skip empty lines and separator lines
        if not line.strip() or re.match(r"^[\s\-+|]+$", line):
            continue

        # Split by multiple spaces or pipe characters
        values = [v.strip() for v in re.split(r"\s{2,}|\|", line) if v.strip()]

        if len(values) < len(headers):
            continue

        # First column should be the username
        username = values[0]
        stats = {}

        for i, header in enumerate(headers[1:], start=1):
            if i < len(values):
                value = values[i]
                # Try to convert to number
                try:
                    if "." in value:
                        stats[header] = float(value)
                    else:
                        stats[header] = int(value)
                except ValueError:
                    stats[header] = value

        if stats:
            user_stats[username] = stats

    return user_stats


def save_output_files(
    local_output: str, released_output: str, output_dir: Path,
) -> tuple[Path, Path]:
    """
    Save outputs to timestamped files.

    Args:
        local_output: Output from local version
        released_output: Output from released version
        output_dir: Directory to save files in

    Returns:
        Tuple of (local_file_path, released_file_path)

    """
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    local_file = output_dir / f"local_output_{timestamp}.txt"
    released_file = output_dir / f"released_output_{timestamp}.txt"

    local_file.write_text(local_output)
    released_file.write_text(released_output)

    return local_file, released_file


def compare_outputs(
    local_stats: dict[str, dict[str, Any]],
    released_stats: dict[str, dict[str, Any]],
) -> tuple[bool, str]:
    """
    Semantically compare two sets of user statistics.

    Args:
        local_stats: Parsed stats from local version
        released_stats: Parsed stats from released version

    Returns:
        Tuple of (are_equal, difference_message)

    """
    differences = []

    # Check for users present in one but not the other
    local_users = set(local_stats.keys())
    released_users = set(released_stats.keys())

    missing_in_released = local_users - released_users
    missing_in_local = released_users - local_users

    if missing_in_released:
        differences.append(
            f"Users in local but not in released: {missing_in_released}",
        )

    if missing_in_local:
        differences.append(
            f"Users in released but not in local: {missing_in_local}",
        )

    # Compare stats for common users
    common_users = local_users & released_users

    for user in sorted(common_users):
        local_user_stats = local_stats[user]
        released_user_stats = released_stats[user]

        # Check for metric differences
        all_metrics = set(local_user_stats.keys()) | set(
            released_user_stats.keys(),
        )

        for metric in sorted(all_metrics):
            local_value = local_user_stats.get(metric)
            released_value = released_user_stats.get(metric)

            if local_value != released_value:
                # For floating point numbers, allow small differences
                if (
                    isinstance(local_value, float)
                    and isinstance(released_value, float)
                    and abs(local_value - released_value) < FLOAT_TOLERANCE
                ):
                    continue

                differences.append(
                    f"User '{user}', metric '{metric}': "
                    f"local={local_value}, released={released_value}",
                )

    if differences:
        return False, "\n".join(differences)

    return True, ""


@pytest.mark.integration
def test_local_vs_released_version() -> None:
    """
    Test that local version produces same output as released version.

    This integration test runs review-tally against the expressjs
    organization for March 2025 using both the local development version
    and the installed released version, then compares the outputs.

    Requires:
        - GITHUB_TOKEN environment variable
        - review-tally command installed (released version)
    """
    # Check for required environment variable
    if "GITHUB_TOKEN" not in os.environ:
        pytest.fail(
            "GITHUB_TOKEN environment variable is required for "
            "integration tests",
        )

    # Test parameters
    org = "expressjs"
    start_date = "2025-11-01"
    end_date = "2025-11-05"
    timeout = 600 * 3 # 10 minutes

    # Prepare output directory
    output_dir = Path(__file__).parent / "outputs"

    # Run local version
    local_cmd = [
        "poetry",
        "run",
        "python",
        "-m",
        "reviewtally.main",
        "-o",
        org,
        "-s",
        start_date,
        "-e",
        end_date,
        "--no-cache",
    ]

    try:
        print(f"\nRunning local version command: {' '.join(local_cmd)}")
        local_result = subprocess.run(
            local_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
        local_output = local_result.stdout
        print(f"\nLocal version output:\n{local_output}")
    except subprocess.CalledProcessError as e:
        pytest.fail(
            f"Local version failed with exit code {e.returncode}:\n"
            f"stdout: {e.stdout}\n"
            f"stderr: {e.stderr}",
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"Local version timed out after {timeout} seconds")

    # Run released version
    released_cmd = [
        "review-tally",
        "-o",
        org,
        "-s",
        start_date,
        "-e",
        end_date,
        "--no-cache",
    ]

    try:
        print(f"\nRunning released version command: {' '.join(released_cmd)}")
        released_result = subprocess.run(
            released_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
        released_output = released_result.stdout
        print(f"\nReleased version output:\n{released_output}")
    except FileNotFoundError:
        pytest.fail(
            "Released version not found. Please install review-tally:\n"
            "  pip install review-tally\n"
            "or:\n"
            "  poetry add --group dev review-tally",
        )
    except subprocess.CalledProcessError as e:
        pytest.fail(
            f"Released version failed with exit code {e.returncode}:\n"
            f"stdout: {e.stdout}\n"
            f"stderr: {e.stderr}",
        )
    except subprocess.TimeoutExpired:
        pytest.fail(f"Released version timed out after {timeout} seconds")

    # Save outputs to files
    local_file, released_file = save_output_files(
        local_output, released_output, output_dir,
    )

    print("\nOutputs saved to:")
    print(f"  Local: {local_file}")
    print(f"  Released: {released_file}")

    # Parse outputs
    local_stats = parse_tabulated_output(local_output)
    released_stats = parse_tabulated_output(released_output)

    # Compare semantically
    are_equal, diff_message = compare_outputs(local_stats, released_stats)

    if not are_equal:
        pytest.fail(
            f"Outputs differ between local and released versions:\n\n"
            f"{diff_message}\n\n"
            f"Full outputs saved to:\n"
            f"  Local: {local_file}\n"
            f"  Released: {released_file}",
        )

    print(
        "\nSuccess! Local and released versions produced identical results.",
    )
    print(f"Compared {len(local_stats)} users across {org} organization.")
