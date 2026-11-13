FROM stage7-engine-clock-base:7da97f743f397971 AS installed
COPY . /sealed/
RUN cd /sealed && sha256sum --strict -c checksums.sha256 \
 && DEBIAN_FRONTEND=noninteractive dpkg --install /sealed/debs/*.deb \
 && mkdir -p /opt/python /opt/hostedtoolcache/Python/3.11.18 \
 && tar --extract --gzip --file=/sealed/python.tar.gz --directory=/opt/python --no-same-owner --same-permissions \
 && ln -s /opt/python /opt/hostedtoolcache/Python/3.11.18/x64 \
 && /opt/python/bin/python3.11 -I -S -B /sealed/installer.py --install-owned-image-stage
FROM stage7-engine-clock-base:7da97f743f397971
COPY --from=installed /usr/ /usr/
COPY --from=installed /etc/ /etc/
COPY --from=installed /var/ /var/
COPY --from=installed /opt/ /opt/
COPY --from=installed /sealed/collector/ /usr/local/libexec/stage7/
COPY --from=installed /sealed/python-layout.json /usr/local/share/stage7/python-layout.json
COPY --from=installed /sealed/renderer-wheels.lock.json /usr/local/share/stage7/renderer-wheels.lock.json
COPY --from=installed /sealed/effective-inputs.lock.json /usr/local/share/stage7/effective-inputs.lock.json
COPY --from=installed /sealed/install-receipt.json /usr/local/share/stage7/install-receipt.json
ARG SOURCE_SHA
LABEL stage7.source=$SOURCE_SHA
ENV LIBGL_ALWAYS_SOFTWARE=1 PYOPENGL_PLATFORM=glx OMP_NUM_THREADS=2
USER 0:0
WORKDIR /
ENTRYPOINT ["/opt/venv/bin/python"]
CMD ["-I", "-S", "-B", "/usr/local/libexec/stage7/scripts/engine_clock_image_inventory.py", "--candidate"]
