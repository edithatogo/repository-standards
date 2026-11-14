fn unsafe_log(key: &str) {
    eprintln!("{:?}", std :: env :: var (key).unwrap());
    std::println!(
        "{:?}",
        std /* comment */ :: env::var_os(key)
    );
}
