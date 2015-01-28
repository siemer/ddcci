ddcci
=====

DDC/CI command line tool.

Depends on loaded i2c-dev module (and the resulting /dev/i2c-? files to
access the i2c bus you pass on the command line).

Does not depend on any smbus python modules or such.

Pretty raw at the moment. – Starting point for improving knowledge beyond
the crappy spec: with real hardware reverse engineering.

I will try to get this working over DisplayPort. The DP AUX channel is
definitively different to work with... and I can’t see the kernel code
which does the legacy i2c mapping... maybe there is none. So I have to
do it in the app.
