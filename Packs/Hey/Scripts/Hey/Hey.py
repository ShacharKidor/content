from io import StringIO
from subprocess import PIPE, Popen

import pandas as pd
import urllib3

import demistomock as demisto  # noqa: F401
from CommonServerPython import *  # noqa: F401

# disable insecure warnings
urllib3.disable_warnings()

# ---------- CLASSES ---------- #


class HeyPerformanceResult:
    def __init__(self,
                 result: str,
                 results_map: Optional[str],
                 t: Optional[str] = None,
                 c: Optional[str] = None,
                 n: Optional[str] = None,
                 **args):
        self._t = int(t or 20)
        self._c = int(c or 50)
        self._n = int(n or 200)
        c_in_n = self._n / self._c
        if c_in_n != int(c_in_n):
            self._n = int(c_in_n) * self._c
        self._result = result or ''
        self._ext_results_map = {}
        if results_map:
            self._ext_results_map = dict(item.split("=") for item in results_map.split(";"))

    def to_results(self) -> CommandResults:
        df = pd.read_csv(StringIO(self._result), usecols=['response-time', 'status-code'])
        requests_num = self._n
        if len(df) == 0:
            max_time = 0
            avg_time = 0
            min_time = 0
            total_time = int(self._n / self._c) * self._t
            successful_responses = 0
        else:
            response_times = df['response-time']
            max_time = max(response_times)
            min_time = min(response_times)
            avg_time = response_times.mean()
            total_time = response_times.sum() / int(self._c)  # not 100% accurate
            status_codes = df.get('status-code')
            successful_responses = len(tuple(code == 200 for code in status_codes))
        outputs = {
            "TimeoutPerRequest": self._t,
            "Concurrency": self._c,
            "Requests": requests_num,
            "SlowestTime": max_time,
            "FastestTime": min_time,
            "AverageTime": avg_time,
            "TotalTime": total_time,
            "SuccessfulResponses": successful_responses
        }
        outputs.update(self._ext_results_map)
        return CommandResults(outputs=outputs, outputs_prefix="Hey")


# ---------- HELPER FUNCTIONS ---------- #

def run_command(command: str) -> str:
    """Run a bash command in the shell.

    Args:
        command (string): The string of the command you want to execute.

    Returns:
        string. The output of the command you are trying to execute.
    """
    p = Popen(command.split(), stdout=PIPE, stderr=PIPE, universal_newlines=True)
    output, err = p.communicate()
    if err:
        raise RuntimeError('Failed to run command {}\nerror details:\n{}'.format(command, err))

    return output


def run_hey_test(url: str, n: Optional[str] = None, t: Optional[str] = None, c: Optional[str] = None,
                 z: Optional[str] = None, m: Optional[str] = None,
                 results_map: Optional[dict] = None) -> CommandResults:
    hey_map = assign_params(
        t=t,
        n=n,
        c=c,
        m=m,
        z=z + 's' if z else None,
        o='csv'
    )
    hey_query = f"hey --disable-compression " + " ".join(f"-{k} {v}" for k, v in hey_map.items()) + f' {url}'
    result = run_command(hey_query)
    return HeyPerformanceResult(result=result, results_map=results_map, **hey_map).to_results()


def main() -> None:
    args = demisto.args()
    try:
        return_results(run_hey_test(**args))
    # Log exceptions and return errors
    except Exception as e:
        demisto.error(traceback.format_exc())  # print the traceback
        return_error(f'Error:\n{str(e)}')


if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
