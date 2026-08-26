import * as tls from "node:tls";

type CertificateSource = "default" | "system" | "bundled" | "extra";
type NodeTlsWithCertificateStore = typeof tls & {
  getCACertificates?: (type?: CertificateSource) => string[];
  setDefaultCACertificates?: (certificates: ReadonlyArray<string | NodeJS.ArrayBufferView>) => void;
};

const nodeTls = tls as NodeTlsWithCertificateStore;

// Node uses its bundled CA list by default, while browsers and curl also trust
// certificates installed in the operating system. Merging both stores keeps
// public HTTPS endpoints working behind a managed/corporate TLS proxy without
// weakening certificate validation.
  try {
    const bundledAndExtra = nodeTls.getCACertificates?.("default") ?? [];
    // Sandboxed Node test workers cannot always access the macOS keychain and
    // may terminate natively before JavaScript can catch the error.
    const system = process.env.NODE_TEST_CONTEXT
      ? []
      : (nodeTls.getCACertificates?.("system") ?? []);
  if (system.length > 0) {
    nodeTls.setDefaultCACertificates?.([...bundledAndExtra, ...system]);
  }
} catch {
  // Older Node versions may not expose the system certificate store. In that
  // case the standard bundled trust store remains active.
}
