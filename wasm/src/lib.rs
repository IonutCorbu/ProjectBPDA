// Code generated by the multiversx-sc build system. DO NOT EDIT.

////////////////////////////////////////////////////
////////////////// AUTO-GENERATED //////////////////
////////////////////////////////////////////////////

// Init:                                 1
// Upgrade:                              1
// Endpoints:                            4
// Async Callback (empty):               1
// Total number of exported functions:   7

#![no_std]

multiversx_sc_wasm_adapter::allocator!();
multiversx_sc_wasm_adapter::panic_handler!();

multiversx_sc_wasm_adapter::endpoints! {
    project
    (
        init => init
        upgrade => upgrade
        test_results => test_results
        generate_test => generate_test
        submit_test => submit_test
        getResults => get_results
    )
}

multiversx_sc_wasm_adapter::async_callback_empty! {}