#[allow(dead_code)]
#[path = "../perfmark/rust/src/lib.rs"]
mod perfmark;

fn main() {
    for n in [0, 1, 4, 6, 8, 9, 16, 64] {
        let labels: Vec<String> = (0..n).map(|j| format!("pcv_{j}")).collect();
        for _ in 0..2 {
            for variant in 0..3 {
                let values: Vec<(&str, i64)> = labels.iter().enumerate().map(|(j, label)| {
                    (label.as_str(), (1_i64 << 54) + j as i64 + if j == n-1 { variant } else { 0 })
                }).collect();
                let _r = perfmark::Region::new_v(&format!("pcvs_{n}"), &values);
                std::hint::black_box(variant);
            }
        }
    }
    println!("PASS: Rust markers with 0..64 PCVs");
}
