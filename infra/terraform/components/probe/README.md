# Sydney regional Cloud Run probe

This component is a disposable diagnostic for the StayLong sandbox. It creates
`staylong-sydney-probe` in `australia-southeast1` using Google's stateless
hello-app image and a temporary public invoker binding. The guarded
`regional-probe` workflow probes `/` anonymously and always destroys the
component afterward. It is not an application deployment target.
