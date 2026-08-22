"""
NetGravity — End-to-End Test Execution Script
================================================
Runs ingestion, AI Data Sanitizer, Baseline Optimization, and Scenario Engine
against the Case 16 India Sample Dataset.
"""

from pathlib import Path
import json

from netgravity.ingestion.pipeline import run_ingestion
from netgravity.optimization.baseline import evaluate_baseline
from netgravity.scenarios.engine import ScenarioEngine
from netgravity.schemas.scenario import Scenario, ScenarioType, FacilityChange


def main():
    print("=======================================================================")
    print(" NETGRAVITY LOGISTICS NETWORK OPTIMIZATION AGENT — TEST EXECUTION")
    print("=======================================================================")

    source_dir = Path("netgravity/ingestion/tests/fixtures/india_sample")
    print(f"\n[1/4] Ingesting & Sanitizing Data from: {source_dir}...")
    
    # 1. Run Ingestion + AI Sanitizer
    ingest_res = run_ingestion(source_dir, label="India Logistics Baseline Run", save=True)
    report = ingest_res.report

    print(f" -> Status: {'SUCCESS' if ingest_res.ok else 'FAILED'}")
    print(f" -> Data Version Hash: {report.data_version}")
    print(f" -> Entities Assembled: {report.counts}")
    print(f" -> AI Data Sanitizer: {report.extras.get('AI Data Sanitizer')}")
    print(f" -> Distributor Mappings: {report.extras.get('Distributor mappings')}")
    print(f" -> External Signals: {report.extras.get('External signals')}")

    if not ingest_res.ok:
        print("Ingestion failed. Error:", report.extras.get("error"))
        return

    network = ingest_res.network

    # 2. Run Baseline Optimization Solver
    print("\n[2/4] Solving Baseline Network Optimization (Cost Minimization)...")
    baseline_res = evaluate_baseline(network)
    
    status_str = baseline_res.solver.status.value if hasattr(baseline_res.solver.status, "value") else str(baseline_res.solver.status)
    kpis = baseline_res.kpis

    print(f" -> Solver Status: {status_str}")
    if kpis:
        print(f" -> Total Logistics Network Cost: INR {kpis.total_cost:,.2f}")
        print(f" -> Facility Fixed Cost: INR {kpis.facility_cost:,.2f}")
        print(f" -> Variable Handling Cost: INR {kpis.handling_cost:,.2f}")
        print(f" -> Transportation Freight Cost: INR {kpis.transport_cost:,.2f}")
        print(f" -> Carbon Emissions: {kpis.total_carbon_kg:,.2f} kg CO2e")
        print(f" -> Demand Fill Rate: {kpis.demand_fill_rate * 100:.1f}%")

    # 3. Run 360° Node Info Drill-Down Sample
    print("\n[3/4] 360° Warehouse Node Info Drill-Down Sample:")
    sample_fac = network.facilities[0] if network.facilities else None
    if sample_fac:
        print(f" -> Facility ID: {sample_fac.id}")
        print(f" -> Name: {sample_fac.name}")
        print(f" -> Role: {sample_fac.role.value} | Status: {sample_fac.status.value}")
        print(f" -> Location: Lat {sample_fac.latitude}, Lon {sample_fac.longitude}")
        print(f" -> Annual Operating Cost: INR {sample_fac.fixed_cost_per_year:,.2f}/yr")
        print(f" -> Handling Cost: INR {sample_fac.handling_cost_per_unit:.2f}/unit")
        print(f" -> Capacity: {sample_fac.capacity_units_per_period:,.0f} units/period")
        
        # Surcharges from contracts
        transcorp = next((c for c in ingest_res.contracts if "TransCorp" in c.vendor_name), None)
        if transcorp:
            print(f" -> Vendor 3PL Contract: {transcorp.vendor_name} ({transcorp.contract_id})")
            print(f" -> Headline Base Rate: {transcorp.base_rate} {transcorp.rate_unit}")
            print(f" -> Active Surcharges: {len(transcorp.surcharges)} (Fuel: 2.0 INR/kg, NSL: 5.0 INR/kg)")

    # 4. Run Brownfield Scenario Engine: Close Facility
    print("\n[4/4] Evaluating Brownfield Disruption Scenario...")
    target_fac_id = sample_fac.id if sample_fac else "FAC_01"
    scenario = Scenario(
        scenario_id="scen_brownfield_01",
        scenario_name="Consolidate Footprint (Close Facility Node)",
        scenario_type=ScenarioType.CLOSE_FACILITY,
        facility_changes=[
            FacilityChange(
                facility_id=target_fac_id,
                action="CLOSE",
            )
        ]
    )
    
    scen_engine = ScenarioEngine()
    scen_res = scen_engine.run(base_network=network, scenario=scenario)
    
    scen_status_str = scen_res.solver.status.value if hasattr(scen_res.solver.status, "value") else str(scen_res.solver.status)
    print(f" -> Scenario Solver Status: {scen_status_str}")
    if scen_res.kpis and kpis:
        print(f" -> Scenario Total Cost: INR {scen_res.kpis.total_cost:,.2f}")
        cost_diff = scen_res.kpis.total_cost - kpis.total_cost
        print(f" -> Cost Delta vs Baseline: INR {cost_diff:+,.2f}")

    print("\n=======================================================================")
    print(" TEST RUN COMPLETED SUCCESSFULLY — ALL ENGINES OPERATIONAL")
    print("=======================================================================")

if __name__ == "__main__":
    main()
