fn unsafe_log(key: &str) {
    let secret = std::env::var(key);
    println!("{:?}", secret);
}
