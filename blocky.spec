# Packit will dynamically update these fields on every new GitHub release.
Name:           blocky
Version:        0
Release:        1%{?dist}
Summary:        Fast and lightweight DNS proxy and ad-blocker for local network

License:        MIT
URL:            https://github.com/0xERR0R/blocky
Source0:        %{url}/archive/v%{version}/%{name}-%{version}.tar.gz

BuildRequires:  golang >= 1.21
BuildRequires:  systemd-rpm-macros
BuildRequires:  systemd

# Ensure the package is only built on Go-supported architectures.
ExclusiveArch:  %{golang_arches_future}

Requires(pre):  shadow-utils
%{?systemd_requires}

%description
Blocky is a DNS proxy and ad-blocker for local networks written in Go.
It features high performance, support for modern protocols (DoH, DoT, DoQ, DoH3),
flexible query routing, group-based blocking, and native Prometheus integration.

%prep
%autosetup -n %{name}-%{version}

%build
# We use standard Fedora Go build flags while allowing Go to download dependencies.
# Note: Copr project must have "Internet access" enabled.
export GO111MODULE=on
export GOPROXY=https://proxy.golang.org,direct
go build \
    -trimpath \
    -ldflags "-X github.com/0xERR0R/blocky/cmd.Version=%{version} -X github.com/0xERR0R/blocky/cmd.BuildTime=$(date -u +%Y%m%d-%H%M%S)" \
    -o %{name} .

%install
# 1. Install executable
install -D -p -m 0755 %{name} %{buildroot}%{_bindir}/%{name}

# 2. Install default configuration
install -d -m 0750 %{buildroot}%{_sysconfdir}/%{name}
cat << 'EOF' > %{buildroot}%{_sysconfdir}/%{name}/config.yml
# Blocky default configuration
upstreams:
  groups:
    default:
      - https://one.one.one.one/dns-query
      - https://dns.google/dns-query

bootstrapDns:
  - https://1.1.1.1/dns-query
  - 8.8.8.8

ports:
  dns: 53
  http: 4000

blocking:
  denylists:
    ads:
      - https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts
  clientGroupsBlock:
    default:
      - ads

prometheus:
  enable: true
  path: /metrics

log:
  level: info
  format: text
EOF

# 3. Install Systemd Service unit file
install -d -m 0755 %{buildroot}%{_unitdir}
cat << 'EOF' > %{buildroot}%{_unitdir}/%{name}.service
[Unit]
Description=Blocky DNS proxy and ad-blocker
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=blocky
Group=blocky
WorkingDirectory=%{_sysconfdir}/%{name}
ExecStart=%{_bindir}/blocky --config %{_sysconfdir}/%{name}/config.yml
Restart=always
RestartSec=5

# Hardening measures
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=%{_sysconfdir}/%{name}

[Install]
WantedBy=multi-user.target
EOF

%pre
# Create system user/group if they don't exist
getent group %{name} >/dev/null || groupadd -r %{name}
getent passwd %{name} >/dev/null || \
    useradd -r -g %{name} -d %{_sysconfdir}/%{name} -s /sbin/nologin \
    -c "System user for %{name} DNS proxy" %{name}
exit 0

%post
%systemd_post %{name}.service

%preun
%systemd_preun %{name}.service

%postun
%systemd_postun_with_restart %{name}.service

%files
%license LICENSE
%doc README.md
%{_bindir}/%{name}
%{_unitdir}/%{name}.service
%dir %attr(0750, %{name}, %{name}) %{_sysconfdir}/%{name}
%config(noreplace) %attr(0640, %{name}, %{name}) %{_sysconfdir}/%{name}/config.yml

%changelog
* Wed Jul 15 2026 Package Maintainer <your-email@example.com> - 0.24-1
- Initial release of blocky for Fedora Copr
