mod env {
    pub fn var(_: &str) -> &'static str { "public" }
}

mod other {
    pub mod env {
        pub fn var(_: &str) -> &'static str { "public" }
    }
}

fn benign_unrelated_env() {
    println!("{:?} {}", '"', env::var("user.name"));
    println!("{}", other::env::var("user.name"));
}
