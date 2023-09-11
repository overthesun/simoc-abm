import gzip, json
import urllib.request
from pathlib import Path
import pytest
from .conftest import get_records_for_config, config_mapping

# ---------------------------------
# Download Simdata from simoc.space
# ---------------------------------

@pytest.fixture(scope="module")
def download_simdata():
    directory = Path.cwd() / 'test' / 'v1_simdata'

    if not directory.exists():
        directory.mkdir(parents=True)

    url = "https://simoc.space/download/simdata/"
    try:
        for simdata_name in config_mapping.values():
            file_path = directory / simdata_name
            if not file_path.exists():
                urllib.request.urlretrieve(url + simdata_name, file_path)
        return True
    except:
        return False

def test_download_simdata(download_simdata):
    assert download_simdata

# -------------------------------------------
# Helper funcs to produce comparision reports
# -------------------------------------------

def load_simdata(stem):
    """Load gzipped simdata file."""
    fname = config_mapping[stem]
    with gzip.open(f'test/v1_simdata/{fname}', 'rb') as f:
        data = json.load(f)
    return data

def lpe(predictions, targets):
    """Lifetime percentage error"""
    _p = abs(sum(predictions))
    _t = abs(sum(targets))
    return 0 if _t == 0 else (_p-_t)/_t * 100

def compare_records(records, stem):
    """Generate a report of the differences between data generated by the
    current model and current active simdata."""

    # Load current simdata
    simdata = load_simdata(stem)
    _n_steps_expected, _last_step_expected = len(simdata['step_num']), simdata['step_num'][-1]
    _n_steps_actual, _last_step_actual = len(records['step_num']), records['step_num'][-1]    
    assert _n_steps_expected == _n_steps_actual, f'Different number of steps: {_n_steps_expected} vs {_n_steps_actual}'
    assert _last_step_expected == _last_step_actual, f'Different last step: {_last_step_expected} vs {_last_step_actual}'

    def _compare_all_fields(records, simdata, _report):
        """Loop through all dicts recursively, calling `lpe` on list and saving to report"""
        for k, v in records.items():
            if isinstance(v, dict):
                _report[k] = _compare_all_fields(v, simdata[k], _report)
            elif isinstance(v, list):
                _report[k] = lpe(v, simdata[k])
        return _report
    
    reports = _compare_all_fields(records['agents'], simdata['agents'], {})
    return reports


def generate_and_compare(stem, save_new_simdata=True):
    """Generate a comparison report for the given config stem."""
    records = get_records_for_config(stem)
    if save_new_simdata:
        with gzip.open(f'test/v1_simdata/{config_mapping[stem]}', 'wt') as f:
            json.dump(records, f, indent=2)
    comparison_report = compare_records(records, stem)
    def _evalutate_report(report):
        if isinstance(report, dict):
            for k, v in report.items():
                return _evalutate_report(v)
        else:
            try:
                if isinstance(report, float):
                    assert abs(report) == 0, f'{stem} error: {report}'
            except AssertionError as e:    
                with open(f'test/v1_simdata/comparison_report_{stem}.json', 'w') as f:
                    json.dump(comparison_report, f, indent=2)
                raise f"{e}: Comparison report saved to test/v1_simdata/comparison_report_{stem}.json"
    _evalutate_report(comparison_report)

@pytest.mark.parametrize("stem", config_mapping.keys())
def test_model_against_remote_simdata(stem):
    generate_and_compare(stem)