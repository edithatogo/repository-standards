fn benign_log() {
    println!("std::env::var( is a public example");
    println!(r#"here is "std::env::var(" sample"#);
    println!("{:?}", "std::env::var(");
    println!("{:?}", 0 /* nested /* comment */ std::env::var("ignored"); */);
    println!("safe"); // std::env::var("ignored");
}
