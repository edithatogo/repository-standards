fn unsafe_raw_log_macro() {
    r#println!("{:?}", std::env::var("TOKEN"));
    std::r#eprintln!("{:?}", std::env::var_os("TOKEN"));
}
