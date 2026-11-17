fn benign_alias_literals() {
    println!("std::r#env::r#var(TOKEN)");
    println!("ok" /* env::var(TOKEN) is a comment */);
    println!("{:?} {}", '"', "env::var(TOKEN) is a string");
}
