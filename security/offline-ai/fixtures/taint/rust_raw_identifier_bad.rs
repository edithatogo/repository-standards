fn unsafe_raw_identifier() {
    eprintln!("{:?} {:?}", '"', std::r#env::r#var("TOKEN"));
    println!("{:?}", std::r#env::r#var::<&str>("TOKEN"));
    println!("{:?}", (std::r#env::r#var)("TOKEN"));
}
