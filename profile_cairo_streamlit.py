import json
import csv
import sys
from collections import defaultdict

import streamlit as st
import matplotlib.pyplot as plt

def load_program_json(program_json_path):
    """
    Loads program.json and returns:
      - offset_to_info: dict {int offset: dict with debug info}
      - program_length: number of instructions in 'data' array
    """
    with open(program_json_path, "r") as f:
        program_data = json.load(f)

    data_array = program_data.get("data", [])
    program_length = len(data_array)

    debug_info = program_data.get("debug_info", {})
    instr_locs = debug_info.get("instruction_locations", {})

    offset_to_info = {}
    for key, val in instr_locs.items():
        int_key = int(key)
        offset_to_info[int_key] = val

    return offset_to_info, program_length

def infer_function_scope(offset, offset_to_info):
    """
    Returns a function scope string for the given offset.
    - If offset has debug info, return its "accessible_scopes"[-1].
    - Otherwise, try neighbors (offset±1, ±2) to guess the same scope.
    - If no inference possible, return "unmapped".
    """
    if offset in offset_to_info:
        info = offset_to_info[offset]
        scopes = info.get("accessible_scopes", [])
        if scopes:
            return scopes[-1]
        return "unmapped"

    # check small neighbors for a clue
    for diff in [1, -1, 2, -2]:
        neighbor = offset + diff
        if neighbor in offset_to_info:
            info = offset_to_info[neighbor]
            scopes = info.get("accessible_scopes", [])
            if scopes:
                return scopes[-1]

    return "unmapped"

def parse_trace_and_profile(trace_csv_path, offset_to_info, program_length):
    """
    Reads trace.csv, counts how many times each PC is executed,
    groups by function scope (with neighbor inference).
    Returns a dict {scope_name: step_count}.
    """
    pc_counts = defaultdict(int)

    # read trace.csv
    with open(trace_csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pc_str = row["pc"]
            # convert from hex or decimal
            pc_val = int(pc_str, 16) if pc_str.startswith("0x") else int(pc_str)
            pc_counts[pc_val] += 1
            
    # aggregate by inferred scope
    scope_counts = defaultdict(int)

    for offset, count in pc_counts.items():
        scope = infer_function_scope(offset, offset_to_info)
        scope_counts[scope] += count

    return scope_counts

def main():
    st.title("Cairo Trace Profiler")

    program_json_path = "task/program.json"
    trace_csv_path = "task/trace.csv"

    if st.button("Run Profiling"):
        # 1) load program.json
        offset_to_info, program_length = load_program_json(program_json_path)

        # 2) parse the trace, produce scope counts
        scope_counts = parse_trace_and_profile(trace_csv_path, offset_to_info, program_length)

        # 3) sort by descending step count
        sorted_scopes = sorted(scope_counts.items(), key=lambda x: -x[1])

        # 4) display as a table
        st.write("## Profiling Results (Scope → Step Count)")
        st.table(sorted_scopes)

        # 5) prepare bar chart
        if len(sorted_scopes) > 0:
            labels, values = zip(*sorted_scopes)
            # for readability, limit to top 20 in the chart
            top_n = 20
            labels = labels[:top_n]
            values = values[:top_n]

            fig, ax = plt.subplots(figsize=(10, 10))
            ax.bar(labels, values, color='skyblue')
            ax.set_xticklabels(labels, rotation=90)
            ax.set_ylabel("Step Count")
            ax.set_title("Top 20 Scopes by Step Count")
            plt.tight_layout()

            st.pyplot(fig)

if __name__ == "__main__":
    main()
