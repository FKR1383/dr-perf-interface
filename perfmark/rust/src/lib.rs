//! perfmark -- mark regions of a Rust program for drperf.
//!
//! ```no_run
//! let st = perfmark::states(&[("n", 1000)]);
//! {
//!     let _r = perfmark::Region::new("bind_batch", "n_entries", st["n"]);
//!     // counted until `_r` is dropped
//! }
//! ```
//! Links dynamically against libperfmark.so; outside DynamoRIO the markers
//! cost one PLT call each.  `Region::new` declares one state, `Region::new_v` several.
use std::collections::HashMap;
use std::ffi::CString;
use std::os::raw::c_char;

#[link(name = "perfmark")]
extern "C" {
    fn perfmark_begin(region: *const c_char, state_name: *const c_char, state_value: i64);
    fn perfmark_begin_v(region: *const c_char, n: i32, names: *const *const c_char, values: *const i64);
    fn perfmark_end(region: *const c_char);
    fn perfmark_state(name: *const c_char, value: *const c_char);
}

/// An open region; closed when dropped.
pub struct Region {
    name: CString,
}

impl Region {
    pub fn new(name: &str, state_name: &str, state_value: i64) -> Region {
        let name = CString::new(name).expect("region name without NUL");
        let sname = CString::new(state_name).expect("state name without NUL");
        unsafe { perfmark_begin(name.as_ptr(), sname.as_ptr(), state_value) };
        Region { name }
    }

    /// Region with several declared integer states; the cost
    /// formula is derived in all of them.
    pub fn new_v(name: &str, states: &[(&str, i64)]) -> Region {
        let name = CString::new(name).expect("region name without NUL");
        let cnames: Vec<CString> =
            states.iter().map(|(k, _)| CString::new(*k).expect("state name without NUL")).collect();
        let ptrs: Vec<*const c_char> = cnames.iter().map(|c| c.as_ptr()).collect();
        let vals: Vec<i64> = states.iter().map(|(_, v)| *v).collect();
        let n = i32::try_from(ptrs.len()).expect("number of states fits the C marker ABI");
        unsafe { perfmark_begin_v(name.as_ptr(), n, ptrs.as_ptr(), vals.as_ptr()) };
        Region { name }
    }

    pub fn plain(name: &str) -> Region {
        Region::new(name, "", 0)
    }

    /// Attach an extra named value to this (open) region; recorded per trigger.
    pub fn state(&self, name: &str, value: &str) {
        let n = CString::new(name).expect("state name without NUL");
        let v = CString::new(value).expect("state value without NUL");
        unsafe { perfmark_state(n.as_ptr(), v.as_ptr()) };
    }
}

impl Drop for Region {
    fn drop(&mut self) {
        unsafe { perfmark_end(self.name.as_ptr()) };
    }
}

/// Parse `K=V` command-line arguments (as appended by `drperf run --state`)
/// over the given defaults.
pub fn states(defaults: &[(&str, i64)]) -> HashMap<String, i64> {
    let mut out: HashMap<String, i64> =
        defaults.iter().map(|(k, v)| (k.to_string(), *v)).collect();
    for a in std::env::args().skip(1) {
        if let Some((k, v)) = a.split_once('=') {
            if let Ok(v) = v.parse::<i64>() {
                out.insert(k.to_string(), v);
            }
        }
    }
    out
}
