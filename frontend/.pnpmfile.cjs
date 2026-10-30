// openapi-typescript builds types with the TypeScript 5 compiler API.
// TypeScript 7's package only exports its version, so this tool keeps 5.9.3.
function readPackage(pkg) {
  if (pkg.name !== 'openapi-typescript') return pkg;
  pkg.dependencies = { ...pkg.dependencies, typescript: '5.9.3' };
  delete pkg.peerDependencies?.typescript;
  return pkg;
}

module.exports = { hooks: { readPackage } };
