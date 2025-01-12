use multiversx_sc_scenario::*;

fn world() -> ScenarioWorld {
    let mut blockchain = ScenarioWorld::new();

    blockchain.register_contract("mxsc:output/project.mxsc.json", project::ContractBuilder);
    blockchain
}

#[test]
fn empty_rs() {
    world().run("scenarios/project.scen.json");
}
